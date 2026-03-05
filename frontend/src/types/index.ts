export type ItemStatus = 'pending' | 'checked' | 'unavailable'
export type MemberRole = 'owner' | 'member'
export type ListStatus = 'active' | 'archived'

export interface UserInfo {
  user_id: string
  name: string
  avatar_url: string | null
}

export interface ListItem {
  id: string
  list_id: string
  name: string
  quantity: string
  status: ItemStatus
  assigned_to: UserInfo | null
  price: number | null
  last_price: number | null
  checked_by: UserInfo | null
  checked_at: string | null
  version: number
  created_at: string
}

export interface Member {
  user_id: string
  name: string
  email: string
  avatar_url: string | null
  role: MemberRole
  joined_at: string
}

export interface ShoppingList {
  id: string
  title: string
  store_name: string
  address?: string
  status: ListStatus
  total_cost: number | null
  created_at: string
  archived_at?: string | null
  role: MemberRole
  members?: Member[]
  items?: ListItem[]
}

export interface AuthUser {
  id: string
  email: string
  name: string
  avatar_url: string | null
}

export type WsEvent =
  | { event: 'item_updated'; data: ListItem }
  | { event: 'item_added'; data: ListItem }
  | { event: 'item_deleted'; data: { item_id: string } }
  | { event: 'item_assigned'; data: ListItem }
  | { event: 'member_joined'; data: Member }
  | { event: 'member_removed'; data: { user_id: string } }
  | { event: 'list_archived'; data: { total_cost: number } }
