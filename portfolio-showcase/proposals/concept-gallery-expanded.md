# Expanded Product Atlas design brief

## Intent

The page should make Aergia feel like one connected job-search system, not a
collection of CV utilities. A visitor should understand the overall promise in
the hero, see the relationship between product areas immediately afterward,
and then be able to inspect each area in increasing detail.

The primary conversion remains creating a workspace. The secondary conversion
is watching the existing 63-second tour. Authorship stays deliberately quiet:
`rmahbub.com` appears as a small navigation link and a footer credit only.

## Information architecture

| Chapter | Visitor question | Product capabilities shown |
| --- | --- | --- |
| Hero | What is Aergia? | CV, Library, application, and tailored output in one visual atlas |
| The system | How do the parts connect? | Dashboard, CVs, Library, Applications, output |
| Author | Can it replace my current CV workflow? | Create/import/duplicate CVs, structured sections, live preview, customization, save, promote, PDF |
| Remember | What stops me repeating work? | Library profile, seven entry categories, direct editing, promote from CV, add to CV |
| Pursue | What happens after the CV exists? | Job context, status/history, search/filter, follow-up, relevance evidence, tailored CV, quality checks, export |
| Tailoring | How much control do I keep? | Standard generation and coding-agent session, editable draft, warnings/notes, accept/reject |
| Trust | What happens to sensitive material? | Account-scoped workspace, ephemeral import credentials, draft review, shared preview/PDF path |
| Tour | Is this the real product? | Existing end-to-end showcase video |

## Visual system

- **Dark foundation:** slate `#14272e` creates a product-showcase atmosphere
  and makes the mostly white application screens visually prominent.
- **Mint action color:** `#a7f3d0` links primary actions, chapter labels,
  connectors, and successful states back to Aergia's current palette.
- **Warm paper sections:** `#f0f1e9` changes the reading rhythm for Library
  and trust content without introducing an unrelated aesthetic.
- **Orange exception:** `#ff855f` is reserved for the hero's core relationship
  and the visible relevance score. It is not used as a generic decoration.
- **Typography:** one neutral sans-serif family with strong scale, weight, and
  outlined display treatment. Supporting copy stays narrow and high-contrast.
- **Shape:** square and lightly bordered surfaces dominate. Rounded cards,
  icon tiles, gradients, and nested containers are deliberately minimized.

## Interaction model

- Header links jump to the four main chapters; the personal-site link remains
  visually distinct.
- Hero primary action routes to registration for signed-out visitors and the
  dashboard for authenticated visitors. The secondary action scrolls to video.
- Product imagery may use a restrained 1–2% hover scale on pointer devices,
  but captions and information must not depend on hover.
- Chapter index links can become a compact sticky rail after the hero on wide
  screens. The current chapter receives a mint underline and text label.
- The tour video remains user-controlled. It should not autoplay with sound.
- Production screenshots should use responsive `<picture>` sources and lazy
  loading below the fold. Hero media should be preloaded or use an optimized
  poster-sized crop.

## Responsive behavior

- The hero changes from copy plus atlas to copy followed by the atlas.
- The four-item chapter index becomes a two-by-two index.
- Annotation labels remain on the builder image, but shorten to one-line
  explanations at narrow widths.
- Capability ledgers become a two-column label/detail pattern.
- The five-step application process stacks vertically in source order.
- Standard and coding-agent tailoring modes stack without changing their order.
- Screenshots retain meaningful focal points through dedicated mobile crops;
  production should not rely solely on `object-fit` for these.

## Accessibility and content rules

- Every screenshot needs alt text describing the product state, not its visual
  styling. Decorative atlas duplicates should use empty alt text.
- Mint-on-dark and dark-on-mint combinations must meet WCAG AA contrast.
- The outlined hero line remains decorative; the complete headline must stay
  available to assistive technology as normal text.
- Navigation, video controls, calls to action, and any future screenshot modal
  require visible keyboard focus states.
- Claims must remain tied to behavior in the repository. Avoid invented usage
  metrics, testimonials, employer logos, or generic AI claims.

## Production adaptation

The concept should become the existing `home` feature rather than a new route.
Authentication-aware CTA behavior, TanStack links, current app tokens, and the
existing showcase video can be carried over from the current `HomePage`.
Static screenshot assets should be exported into `web/public/showcase/` only
after the final direction and crops are approved.
