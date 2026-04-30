import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://gdzie-konferencje.pl',
  trailingSlash: 'always',
  integrations: [
    mdx(),
    tailwind({ applyBaseStyles: false }),
  ],
  output: 'static',
});
