import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { updateCV } from "@/features/cvs";
import type { CVDetail } from "@/features/cvs";
import { useBuilderDocumentStore } from "../state/builderDocumentStore";
import { useUnsavedChanges, type BuilderSaveData } from "./useUnsavedChanges";

interface UseBuilderPersistenceOptions {
  id: string;
  instances: BuilderSaveData["sections"];
  customizations: BuilderSaveData["customizations"];
  ready?: boolean;
  syncBuilderDraft: (cv: CVDetail) => void;
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (date: Date) => void;
  refreshApplicationAnalysis: () => Promise<void>;
}

export interface SaveRevisionToken {
  cvId: string;
  generation: number;
  dirtyVersion: number;
  revision: number;
  sequence: number;
}

interface EnqueuedSave {
  cv: CVDetail;
  dirtyVersion: number;
  revisionToken: SaveRevisionToken;
  refreshError: unknown | null;
}

export interface SavedReviewRevision {
  revision: number;
  token: SaveRevisionToken;
}

interface ActiveResource {
  id: string;
  generation: number;
  mounted: boolean;
  ready: boolean;
}

interface ResourceState<T> {
  cvId: string;
  value: T;
}

export interface BuilderPersistence {
  hasUnsavedChanges: boolean;
  markDirty: () => void;
  markClean: () => void;
  handleSave: () => Promise<void>;
  saveForTailoringReview: (expectedCvId: string) => Promise<SavedReviewRevision>;
  syncSavedDocument: (cv: CVDetail, token: SaveRevisionToken, expectedResultRevision?: number) => boolean;
  instancesRef: React.MutableRefObject<BuilderSaveData["sections"]>;
  customizationsRef: React.MutableRefObject<BuilderSaveData["customizations"]>;
  showSavedFeedback: boolean;
  saveError: string | null;
}

const SAVE_ERROR_MESSAGE = "The CV could not be saved. Your edits are still here; try saving again.";

/** Owns dirty tracking, ordered saves, and save feedback for one Builder document. */
export function useBuilderPersistence({
  id,
  instances,
  customizations,
  ready = true,
  syncBuilderDraft,
  setIsSaving,
  setLastSaved,
  refreshApplicationAnalysis,
}: UseBuilderPersistenceOptions): BuilderPersistence {
  const [savedFeedbackState, setSavedFeedbackState] = useState<ResourceState<boolean>>({ cvId: id, value: false });
  const [saveErrorState, setSaveErrorState] = useState<ResourceState<string | null>>({ cvId: id, value: null });
  const showSavedFeedback = savedFeedbackState.cvId === id && savedFeedbackState.value;
  const saveError = saveErrorState.cvId === id ? saveErrorState.value : null;
  const setShowSavedFeedback = useCallback((value: boolean) => setSavedFeedbackState({ cvId: id, value }), [id]);
  const setSaveError = useCallback((value: string | null) => setSaveErrorState({ cvId: id, value }), [id]);
  const activeResourceRef = useRef<ActiveResource>({ id, generation: 0, mounted: false, ready: false });
  const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
  const activeSaveCountsRef = useRef(new Map<string, number>());
  const failedSaveRef = useRef(new Map<string, unknown>());
  const dirtyVersionRef = useRef(0);
  const saveSequenceRef = useRef(0);
  const lastSyncedSaveRef = useRef(new Map<string, { revision: number; sequence: number }>());
  const feedbackTimerRef = useRef<number | null>(null);
  const instancesRef = useRef(instances);
  const customizationsRef = useRef(customizations);
  const instancesForUnloadRef = useRef<BuilderSaveData>({ sections: instances, customizations });

  useLayoutEffect(() => {
    const generation = activeResourceRef.current.generation + 1;
    activeResourceRef.current = { id, generation, mounted: true, ready: false };
    dirtyVersionRef.current = 0;
    saveSequenceRef.current = 0;
    lastSyncedSaveRef.current.delete(id);
    // These UI states belong to one committed route generation, even when a CV ID is reopened.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear feedback owned by the previous route resource
    setSavedFeedbackState({ cvId: id, value: false });
    setSaveErrorState({ cvId: id, value: null });
    return () => {
      if (activeResourceRef.current.generation === generation) {
        activeResourceRef.current = { id, generation: generation + 1, mounted: false, ready: false };
      }
      if (feedbackTimerRef.current !== null) {
        window.clearTimeout(feedbackTimerRef.current);
        feedbackTimerRef.current = null;
      }
    };
  }, [id]);

  useLayoutEffect(() => {
    const current = activeResourceRef.current;
    if (current.id === id && current.mounted) current.ready = ready;
  }, [id, ready]);

  useLayoutEffect(() => {
    instancesRef.current = instances;
    instancesForUnloadRef.current = {
      sections: instances,
      customizations: customizationsRef.current,
    };
  }, [instances]);

  useLayoutEffect(() => {
    customizationsRef.current = customizations;
    instancesForUnloadRef.current = {
      sections: instancesRef.current,
      customizations,
    };
  }, [customizations]);

  const getPendingSaveData = useCallback(() => instancesForUnloadRef.current, []);

  const isCurrentResource = useCallback((cvId: string, generation?: number, requireReady = false) => {
    const resource = activeResourceRef.current;
    return resource.mounted
      && resource.id === cvId
      && (generation === undefined || resource.generation === generation)
      && (!requireReady || resource.ready)
      && useBuilderDocumentStore.getState().currentCV?.id === cvId;
  }, []);

  const syncSavedDocument = useCallback((cv: CVDetail, token: SaveRevisionToken, expectedResultRevision = token.revision) => {
    const lastSynced = lastSyncedSaveRef.current.get(token.cvId);
    if (
      cv.id !== token.cvId
      || cv.revision !== expectedResultRevision
      || expectedResultRevision < token.revision
      || token.cvId !== id
      || token.dirtyVersion !== dirtyVersionRef.current
      || !isCurrentResource(token.cvId, token.generation, true)
      || (lastSynced && (token.sequence < lastSynced.sequence || expectedResultRevision < lastSynced.revision))
    ) return false;

    const current = useBuilderDocumentStore.getState().currentCV;
    if (!current || current.id !== cv.id || current.revision > cv.revision) return false;

    useBuilderDocumentStore.setState((state) => (
      state.currentCV?.id === cv.id && state.currentCV.revision <= cv.revision
        ? { currentCV: cv }
        : {}
    ));
    instancesRef.current = cv.sections;
    customizationsRef.current = cv.customizations;
    instancesForUnloadRef.current = { sections: cv.sections, customizations: cv.customizations };
    syncBuilderDraft(cv);
    lastSyncedSaveRef.current.set(token.cvId, { revision: cv.revision, sequence: token.sequence });
    return true;
  }, [id, isCurrentResource, syncBuilderDraft]);

  const enqueueSave = useCallback((
    cvId: string,
    getSaveData: () => BuilderSaveData,
    allowRecovery = false,
  ): Promise<EnqueuedSave> => {
    const resource = activeResourceRef.current;
    if (!resource.mounted || resource.id !== cvId || !resource.ready) {
      return Promise.reject(new Error("The builder document is still loading. Try again when it is ready."));
    }
    const generation = resource.generation;
    const countKey = `${generation}:${cvId}`;
    const sequence = ++saveSequenceRef.current;
    const count = (activeSaveCountsRef.current.get(countKey) ?? 0) + 1;
    activeSaveCountsRef.current.set(countKey, count);
    if (isCurrentResource(cvId, generation, true)) setIsSaving(true);

    const request = saveQueueRef.current.then(async () => {
      if (!isCurrentResource(cvId, generation, true)) {
        throw new Error("The builder document changed before it could be saved.");
      }
      const previousFailure = failedSaveRef.current.get(countKey);
      if (previousFailure && !allowRecovery) {
        throw previousFailure instanceof Error
          ? previousFailure
          : new Error(SAVE_ERROR_MESSAGE);
      }

      const dirtyVersion = dirtyVersionRef.current;
      let saved: CVDetail;
      try {
        saved = await updateCV(cvId, getSaveData());
      } catch (error) {
        if (isCurrentResource(cvId, generation)) {
          failedSaveRef.current.set(countKey, error);
          setSaveError(SAVE_ERROR_MESSAGE);
        }
        throw error;
      }

      if (allowRecovery) failedSaveRef.current.delete(countKey);
      const revisionToken: SaveRevisionToken = {
        cvId,
        generation,
        dirtyVersion,
        revision: saved.revision,
        sequence,
      };
      syncSavedDocument(saved, revisionToken);

      if (isCurrentResource(cvId, generation)) {
        setLastSaved(new Date());
      }

      let refreshError: unknown | null = null;
      if (isCurrentResource(cvId, generation)) {
        try {
          await refreshApplicationAnalysis();
        } catch (error) {
          refreshError = error;
        }
      }

      return { cv: saved, dirtyVersion, revisionToken, refreshError };
    });

    saveQueueRef.current = request.then(() => undefined, () => undefined);
    const finish = () => {
      const nextCount = Math.max(0, (activeSaveCountsRef.current.get(countKey) ?? 1) - 1);
      if (nextCount === 0) activeSaveCountsRef.current.delete(countKey);
      else activeSaveCountsRef.current.set(countKey, nextCount);
      if (isCurrentResource(cvId, generation)) setIsSaving(nextCount > 0);
    };
    void request.then(finish, finish);
    return request;
  }, [isCurrentResource, refreshApplicationAnalysis, setIsSaving, setLastSaved, setSaveError, syncSavedDocument]);

  const triggerSave = useCallback(async (saveData: BuilderSaveData) => {
    const generation = activeResourceRef.current.generation;
    const saved = await enqueueSave(id, () => saveData);
    if (!isCurrentResource(id, generation, true)) {
      throw new Error("The builder document changed before its save finished.");
    }
    if (saved.dirtyVersion !== dirtyVersionRef.current) {
      throw new Error("The CV changed while it was being saved. Save again before leaving the builder.");
    }
    if (saved.refreshError) throw saved.refreshError;
  }, [enqueueSave, id, isCurrentResource]);

  // The blocker uses the same serialized save path as the visible Save action.
  const persistence = useUnsavedChanges({
    enabled: Boolean(id) && ready,
    resetKey: id,
    getPendingSaveData,
    save: triggerSave,
  });
  const { hasUnsavedChanges, markClean: markPersistenceClean, markDirty: markPersistenceDirty } = persistence;

  const markCleanForCurrent = useCallback(() => {
    if (isCurrentResource(id)) markPersistenceClean();
  }, [id, isCurrentResource, markPersistenceClean]);

  const trackDirty = useCallback(() => {
    if (!isCurrentResource(id, undefined, true)) return;
    dirtyVersionRef.current += 1;
    markPersistenceDirty();
    setSaveError(null);
  }, [id, isCurrentResource, markPersistenceDirty, setSaveError]);

  const handleSave = useCallback(async () => {
    const saved = await enqueueSave(id, () => ({
      sections: instancesRef.current,
      customizations: customizationsRef.current,
    }), true);
    if (saved.dirtyVersion === dirtyVersionRef.current && isCurrentResource(id, saved.revisionToken.generation)) {
      markPersistenceClean();
      setSaveError(null);
      setShowSavedFeedback(true);
      if (feedbackTimerRef.current !== null) window.clearTimeout(feedbackTimerRef.current);
      feedbackTimerRef.current = window.setTimeout(() => {
        if (isCurrentResource(id, saved.revisionToken.generation)) setShowSavedFeedback(false);
        feedbackTimerRef.current = null;
      }, 2000);
    }
  }, [enqueueSave, id, isCurrentResource, markPersistenceClean, setSaveError, setShowSavedFeedback]);

  const saveForTailoringReview = useCallback(async (expectedCvId: string): Promise<SavedReviewRevision> => {
    if (expectedCvId !== id) throw new Error("The builder document changed before it could be reviewed.");
    const generation = activeResourceRef.current.generation;
    const saved = await enqueueSave(expectedCvId, () => ({
      sections: instancesRef.current,
      customizations: customizationsRef.current,
    }));
    if (!isCurrentResource(expectedCvId, generation, true)) {
      throw new Error("The builder document changed before its saved revision could be reviewed.");
    }
    if (saved.dirtyVersion !== dirtyVersionRef.current) {
      throw new Error("The CV changed while it was being saved. Save the latest edits before reevaluating.");
    }
    markCleanForCurrent();
    if (saved.refreshError) throw saved.refreshError;
    return { revision: saved.cv.revision, token: saved.revisionToken };
  }, [enqueueSave, id, isCurrentResource, markCleanForCurrent]);

  return {
    hasUnsavedChanges,
    markDirty: trackDirty,
    markClean: markCleanForCurrent,
    handleSave,
    saveForTailoringReview,
    syncSavedDocument,
    instancesRef,
    customizationsRef,
    showSavedFeedback,
    saveError,
  };
}
