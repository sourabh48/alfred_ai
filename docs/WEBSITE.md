# Website and search visibility

Product website: https://sourabh48.github.io/alfred_ai/

Installation guide: https://sourabh48.github.io/alfred_ai/guide/

GitHub renders `README.md` at the repository URL. It does not execute HTML there.
The public website uses GitHub Pages with `master` and `/docs` as its source;
`.nojekyll` serves the authored HTML directly. This publishes documentation only.
The application and all user data continue to run locally or on the chosen LAN.
The packaged `guide/index.html` also works offline.

Both HTML pages have descriptive titles, descriptions, canonical HTTPS URLs,
indexable robots metadata, semantic headings, image descriptions and social
sharing metadata. The homepage includes factual SoftwareApplication JSON-LD;
no ratings or reviews are fabricated. `sitemap.xml` lists the two public pages.

Google does not guarantee discovery, indexing, rankings or rich results. The
site can be submitted as a URL-prefix property in Google Search Console:

1. Add `https://sourabh48.github.io/alfred_ai/` to your own Search Console account.
2. Obtain Google's verification HTML file or meta tag and add it to `docs`.
3. Push the change, complete verification and submit `sitemap.xml`.
4. Inspect the homepage and guide URLs and request indexing if needed.

No Search Console ownership token is configured yet. A project-level
`/alfred_ai/robots.txt` would not control the host: crawlers look at the domain's
root `/robots.txt`. The HTML metadata and sitemap provide the relevant signals.

References: [GitHub Pages publishing sources](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site),
[Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
[Google software application markup](https://developers.google.com/search/docs/appearance/structured-data/software-app).
