import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ListsPage } from './pages/ListsPage'
import { ListDetailPage } from './pages/ListDetailPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <div style={{ padding: '40px', textAlign: 'center', color: '#9ca3af' }}>Carregando...</div>
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/lists"
        element={<PrivateRoute><ListsPage /></PrivateRoute>}
      />
      <Route
        path="/lists/:listId"
        element={<PrivateRoute><ListDetailPage /></PrivateRoute>}
      />
      <Route path="*" element={<Navigate to="/lists" replace />} />
    </Routes>
  )
}
