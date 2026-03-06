import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import type { WsEvent, ListItem } from '../types'

const FILTERS = ['all', 'mine'] as const

export function useListWebSocket(listId: string, token: string | null, userId: string | null) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
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
          // Update in-place em ambos os caches (status/price não afeta quem é dono)
          for (const f of FILTERS) {
            queryClient.setQueryData<ListItem[]>(
              ['list', listId, 'items', f],
              (old) => old?.map((i) => (i.id === msg.data.id ? msg.data : i))
            )
          }
          break

        case 'item_assigned': {
          const updated = msg.data

          // cache 'all': update in-place (item sempre existe aqui)
          queryClient.setQueryData<ListItem[]>(
            ['list', listId, 'items', 'all'],
            (old) => old?.map((i) => (i.id === updated.id ? updated : i))
          )

          // cache 'mine': filter-aware — add se agora é meu, remove se deixou de ser
          queryClient.setQueryData<ListItem[]>(
            ['list', listId, 'items', 'mine'],
            (old = []) => {
              const isNowMine = updated.assigned_to?.user_id === userId
              const alreadyInMine = old.some((i) => i.id === updated.id)

              if (isNowMine && !alreadyInMine) return [...old, updated]
              if (isNowMine && alreadyInMine) return old.map((i) => (i.id === updated.id ? updated : i))
              return old.filter((i) => i.id !== updated.id)
            }
          )
          break
        }

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

        case 'list_deleted':
          // Remove os dados desta lista do cache — sem refetch (404 seria retornado)
          queryClient.removeQueries({ queryKey: ['list', listId] })
          queryClient.removeQueries({ queryKey: ['list', listId, 'items'] })
          // Invalida a listagem para remover o card da home
          queryClient.invalidateQueries({ queryKey: ['lists'] })
          // Redireciona sem deixar histórico desta lista (replace)
          navigate('/lists', { replace: true })
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
  }, [listId, token, userId, queryClient, navigate])
}
