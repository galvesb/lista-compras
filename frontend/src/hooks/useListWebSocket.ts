import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { WsEvent, ListItem } from '../types'

const FILTERS = ['all', 'mine'] as const

export function useListWebSocket(listId: string, token: string | null) {
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!token || !listId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/lists/${listId}?token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data) as WsEvent

      switch (msg.event) {
        case 'item_updated':
        case 'item_assigned':
          // Update item in all cached filter variants immediately (no refetch)
          for (const f of FILTERS) {
            queryClient.setQueryData<ListItem[]>(
              ['list', listId, 'items', f],
              (old) => old?.map((i) => (i.id === msg.data.id ? msg.data : i))
            )
          }
          break

        case 'item_added':
          // Append to 'all' cache, deduplicating to avoid double-insert
          // (mutation onSuccess already adds it optimistically for the actor)
          queryClient.setQueryData<ListItem[]>(
            ['list', listId, 'items', 'all'],
            (old) => {
              if (!old) return [msg.data]
              if (old.some((i) => i.id === msg.data.id)) return old
              return [...old, msg.data]
            }
          )
          queryClient.invalidateQueries({ queryKey: ['list', listId, 'items', 'mine'] })
          break

        case 'item_deleted':
          for (const f of FILTERS) {
            queryClient.setQueryData<ListItem[]>(
              ['list', listId, 'items', f],
              (old) => old?.filter((i) => i.id !== msg.data.item_id)
            )
          }
          break

        case 'member_joined':
        case 'member_removed':
          queryClient.invalidateQueries({ queryKey: ['list', listId] })
          break

        case 'list_archived':
          queryClient.invalidateQueries({ queryKey: ['lists'] })
          queryClient.invalidateQueries({ queryKey: ['list', listId] })
          break
      }
    }

    ws.onerror = () => ws.close()

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 30_000)

    return () => {
      clearInterval(ping)
      ws.close()
    }
  }, [listId, token, queryClient])
}
