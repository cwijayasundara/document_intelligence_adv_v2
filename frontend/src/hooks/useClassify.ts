/** TanStack Query hooks for classification operations. */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { triggerClassify } from "../lib/api/classify";
import type { ClassifyResponse } from "../types/classify";

const CLASSIFY_KEY = ["classify"] as const;

/** Trigger document classification. */
export function useTriggerClassify() {
  const queryClient = useQueryClient();
  return useMutation<ClassifyResponse, Error, string>({
    mutationFn: (id: string) => triggerClassify(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: [...CLASSIFY_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
