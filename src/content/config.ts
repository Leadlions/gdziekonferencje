import { defineCollection, z } from 'astro:content';

const specjalizacje = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    displayName: z.string(),
    keywords: z.array(z.string()).optional(),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
  }),
});

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
    tags: z.array(z.string()).optional(),
    author: z.string().default('Redakcja gdzie-konferencje.pl'),
  }),
});

export const collections = { specjalizacje, blog };
