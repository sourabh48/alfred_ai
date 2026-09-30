# Bundled browser libraries

These assets allow the interface, dialogs and charts to work without a CDN.

- Bootstrap 5.3.2: https://github.com/twbs/bootstrap/tree/v5.3.2 (MIT; bootstrap-LICENSE).
- Chart.js 4.5.1: https://github.com/chartjs/Chart.js/tree/v4.5.1 (MIT; chartjs-LICENSE).
- Leaflet 1.9.4: https://github.com/Leaflet/Leaflet/tree/v1.9.4 (BSD-2-Clause; leaflet/LICENSE).
  JS/CSS fetched from pinned unpkg distribution. SHA256 JS:
  db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a;
  CSS: a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6.
  Travel maps use circle markers; no remote marker-image dependency. Tile loading
  is opt-in and follows the configured tile provider policy.

Downloaded from the corresponding pinned npm package URLs at cdn.jsdelivr.net.
Optional Google web fonts fall back to system fonts when offline.
