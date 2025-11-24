import { z } from 'zod';

export type EffortSize = "S" | "M" | "L";

export const DeliverableSchema = z.object({
  id: z.string(),
  label: z.string(),
  acceptanceCriteria: z.array(z.string()).optional(),
});

export type Deliverable = z.infer<typeof DeliverableSchema>;

export const DependencyRefSchema = z.object({
  id: z.string(),
  type: z.enum(["needs", "feeds"]),
});

export type DependencyRef = z.infer<typeof DependencyRefSchema>;

export const RoleEffortSchema = z.object({
  role: z.string(),
  hours: z.number().optional(),
  seniority: z.enum(["Jr", "Mid", "Sr"]).optional(),
});

export type RoleEffort = z.infer<typeof RoleEffortSchema>;

export const ModuleSchema = z.object({
  id: z.string(),
  title: z.string(),
  valueStatement: z.string(),
  effort: z.object({
    size: z.enum(["S", "M", "L"]).optional(),
    hoursMin: z.number().optional(),
    hoursMax: z.number().optional(),
  }).optional(),
  outputs: z.array(DeliverableSchema),
  activities: z.array(z.string()),
  risks: z.array(z.string()).optional(),
  assumptions: z.array(z.string()).optional(),
  dependencies: z.array(DependencyRefSchema).optional(),
  roles: z.array(RoleEffortSchema).optional(),
  channels: z.array(z.string()).optional(),
  phase: z.enum(["Discovery", "Concept", "Review", "Production"]).optional(),
  department: z.string().optional(),
});

export type Module = z.infer<typeof ModuleSchema>;

export const ScopeSummarySchema = z.object({
  title: z.string(),
  markets: z.array(z.string()).optional(),
  channels: z.array(z.string()).optional(),
  complexity: z.enum(["Low", "Medium", "High"]).optional(),
  modules: z.array(ModuleSchema),
});

export type ScopeSummary = z.infer<typeof ScopeSummarySchema>;
