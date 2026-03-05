import type { UserInfo } from '../types'

interface AvatarProps {
  user: UserInfo
  size?: 'sm' | 'md'
  title?: string
}

export function Avatar({ user, size = 'sm', title }: AvatarProps) {
  const dim = size === 'sm' ? '28px' : '40px'
  const fontSize = size === 'sm' ? '11px' : '16px'

  const initials = user.name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()

  const style: React.CSSProperties = {
    width: dim,
    height: dim,
    borderRadius: '50%',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize,
    fontWeight: 600,
    flexShrink: 0,
    objectFit: 'cover',
    background: user.avatar_url ? 'transparent' : '#6366f1',
    color: '#fff',
  }

  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.name}
        title={title ?? user.name}
        style={style as React.CSSProperties}
      />
    )
  }

  return (
    <span style={style} title={title ?? user.name}>
      {initials}
    </span>
  )
}
