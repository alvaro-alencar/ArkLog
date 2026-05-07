import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Login from './Login'

vi.mock('lucide-react', () => ({
  Github: () => <div data-testid="github-icon" />,
}))

describe('Login View', () => {
  it('deve renderizar o título e o botão de login', () => {
    render(<Login />)
    
    expect(screen.getByText('ArkLog')).toBeInTheDocument()
    expect(screen.getByText('Continue with GitHub')).toBeInTheDocument()
  })

  it('deve redirecionar para a API ao clicar no botão', () => {
    const originalLocation = window.location
    // @ts-ignore
    delete window.location
    // @ts-ignore
    window.location = { href: '' }

    render(<Login />)
    
    const loginBtn = screen.getByText('Continue with GitHub')
    loginBtn.click()

    expect(window.location.href).toBe('/api/v1/auth/login/github')
    
    window.location = originalLocation
  })
})
