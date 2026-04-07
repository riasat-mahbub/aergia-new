# Fix: BuilderPage "CV not found" — early return blocks useEffect from running

## Root Cause (CONFIRMED)
The early return guard at line 32-43 in `BuilderPage.tsx` short-circuits the component **before** any hooks below it execute. In React, hooks must run unconditionally on every render. An early return prevents:
1. `useState` calls below the guard from being initialized
2. `useEffect` at line 55 from being scheduled — this is where `loadCV(id)` lives

So the flow is:
1. Component mounts with `isLoading=false`, `currentCV=null` (initial store state)
2. Guard condition `isLoading || !currentCV` is true → returns early
3. **useEffect never runs** → `loadCV()` never called → no API request made
4. Store state never changes → stuck on "CV not found" forever

This is why replacing `useParams()` with `useLocation().pathname.split()` didn't help — both work fine. The ID was always correct; the effect just never ran.

## Fix

### In `web/src/pages/BuilderPage.tsx`:

**1. Remove the early return guard (lines 32-43)** and add a `showLoading` state:
```diff
  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useCVStore();

- // Guard before any state logic — prevents null access during loading/navigation
- if (isLoading || !currentCV) {
-   return (
-     <motion.div
-       initial={{ opacity: 0 }}
-       animate={{ opacity: 1 }}
-       className="flex h-screen items-center justify-center"
-     >
-       <p className="text-gray-500">{isLoading ? "Loading CV..." : "CV not found"}</p>
-     </motion.div>
-   );
- }
-
  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
```

**2. Add `showLoading` state right after the store hook:**
```diff
+  const [showLoading, setShowLoading] = useState(true);
+  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
```

**3. Set `showLoading` to false when `currentCV` loads (in the effect at line 63-71):**
Change the async block in the effect:
```diff
    (async () => {
      await loadCV(id);
+     setShowLoading(false);
      if (cancelled) return;
      const state = useCVStore.getState();
```

**4. Move the loading guard into the JSX return, before accessing `currentCV`:**
In the return JSX (line 297), add a loading check at the top:
```diff
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
+   {showLoading ? (
+     <motion.div
+       initial={{ opacity: 0 }}
+       animate={{ opacity: 1 }}
+       className="flex h-screen items-center justify-center"
+     >
+       <p className="text-gray-500">Loading CV...</p>
+     </motion.div>
+   ) : (
      <div className="flex h-screen flex-col">
        ...
      </div>
+   )}
    </DndContext>
  );
```

**5. Also guard `currentCV` accesses in JSX with optional chaining or a null check before the showLoading block**, since `currentCV` could still be null after loading fails:
Wrap the main content in a conditional that also checks `currentCV`:
```tsx
{showLoading ? (
  <motion.div ...><p>Loading CV...</p></motion.div>
) : currentCV ? (
  <div className="flex h-screen flex-col">...</div>
) : (
  <motion.div ...><p>CV not found</p></motion.div>
)}
```

## Files to modify
- `web/src/pages/BuilderPage.tsx` — remove early return, add showLoading state, move guard into JSX

## Verification
1. Start backend + frontend
2. Create a new CV → navigate to builder → should show "Loading CV..." briefly then load
3. Click edit on existing CV → same flow, no "CV not found" error
4. Network tab shows `GET /api/v1/cvs/{id}` succeeding with 200
