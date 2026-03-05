import { api } from './client'
import type { ItemStatus, ListItem } from '../types'

export interface UpdateItemPayload {
  version: number
  status?: ItemStatus
  price?: number
}

export const itemsApi = {
  list: (listId: string, filter?: 'mine') =>
    api.get<ListItem[]>(`/lists/${listId}/items`, {
      params: filter ? { filter } : undefined,
    }).then((r) => r.data),

  add: (listId: string, name: string, quantity: string) =>
    api.post<ListItem>(`/lists/${listId}/items`, { name, quantity }).then((r) => r.data),

  update: (listId: string, itemId: string, payload: UpdateItemPayload) =>
    api.patch<ListItem>(`/lists/${listId}/items/${itemId}`, payload).then((r) => r.data),

  assign: (listId: string, itemId: string, userId: string | null) =>
    api.patch<ListItem>(`/lists/${listId}/items/${itemId}/assign`, { user_id: userId }).then((r) => r.data),

  delete: (listId: string, itemId: string) =>
    api.delete(`/lists/${listId}/items/${itemId}`),
}
