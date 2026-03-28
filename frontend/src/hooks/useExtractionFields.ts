/** TanStack Query hooks for extraction field operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFields, fetchFields } from "../lib/api/config";
import type { FieldCreateRequest, FieldsListResponse } from "../types/config";

const FIELDS_KEY = ["extraction-fields"] as const;

export function useExtractionFields(categoryId: string) {
  return useQuery<FieldsListResponse>({
    queryKey: [...FIELDS_KEY, categoryId],
    queryFn: () => fetchFields(categoryId),
    enabled: !!categoryId,
  });
}

export function useCreateFields() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      categoryId,
      fields,
    }: {
      categoryId: string;
      fields: FieldCreateRequest[];
    }) => createFields(categoryId, fields),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: FIELDS_KEY });
    },
  });
}
