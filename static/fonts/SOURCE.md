# IBM Plex Sans webfont provenance

The four WOFF2 files in this directory are unmodified complete-glyph webfonts
from IBM's official `@ibm/plex-sans@1.1.0` package, published from the
[`IBM/plex`](https://github.com/IBM/plex) repository under SIL OFL 1.1.
They are self-hosted so the DevLink interface makes no runtime font request to
a third party.

Pinned package record: `https://www.npmjs.com/package/@ibm/plex-sans/v/1.1.0`

| Local file | Package path / exact retrieval origin | SHA-256 |
|---|---|---|
| `ibm-plex-sans-regular.woff2` | `https://unpkg.com/@ibm/plex-sans@1.1.0/fonts/complete/woff2/IBMPlexSans-Regular.woff2` | `BA711A3085FF9F27440B6B9C4550CFC47C97BF36591D5DA958B975BB3ADD8C1A` |
| `ibm-plex-sans-medium.woff2` | `https://unpkg.com/@ibm/plex-sans@1.1.0/fonts/complete/woff2/IBMPlexSans-Medium.woff2` | `5660F8A658F8BB50DBC005232F885EADFFD2BC1C235C4F6FBB63469D1F9CDE6D` |
| `ibm-plex-sans-semibold.woff2` | `https://unpkg.com/@ibm/plex-sans@1.1.0/fonts/complete/woff2/IBMPlexSans-SemiBold.woff2` | `F78048030EAB62E860EFA39A0DF79E2E5581BF122EB95B9BC42C0B8A4988D205` |
| `ibm-plex-sans-bold.woff2` | `https://unpkg.com/@ibm/plex-sans@1.1.0/fonts/complete/woff2/IBMPlexSans-Bold.woff2` | `FA7130D854A660B39A7FC9E6E0F2DC23DBA5F1346E2ADEA3E1FE37B6D884133D` |

The package's complete WOFF2 builds were selected instead of language subsets
so every Spanish codepoint already present in the site remains available.
`fontTools` inspection found 928 mapped codepoints in each file and confirmed
coverage for accented Spanish letters, `ñ`, `ü`, inverted punctuation, the
copyright sign, en/em dashes, and the arrow used by the interface.

No font file was converted, subset, renamed internally, or otherwise modified.
The original package license is preserved verbatim in `OFL.txt`.
