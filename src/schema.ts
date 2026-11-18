import { z } from "zod";

export const InjurySchema = z.object({
  injury: z.string().nullable(),
  bodyPart: z.string().nullable(),
  severity: z.number().int().min(1).max(10).nullable(),
  cause: z.string().nullable(),
  date: z.string().nullable(),
});

export type Injury = z.infer<typeof InjurySchema>;
