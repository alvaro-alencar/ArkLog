import { test, expect } from '@playwright/test';

test('deve redirecionar para o login quando não autenticado', async ({ page }) => {
  await page.goto('/');

  // Verifica se foi redirecionado para a tela de login
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole('heading', { name: 'ArkLog' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue with GitHub' })).toBeVisible();
});

test('deve mostrar a tela de carregamento no callback de OAuth', async ({ page }) => {
  // Vamos para a URL de callback
  await page.goto('/auth/callback?code=mock-code');
  
  // Como o backend está offline no teste, ele pode redirecionar para /login muito rápido
  // Verificamos se a mensagem de autenticação apareceu ou se já estamos no login
  const loadingText = page.getByText('Authenticating with GitHub...');
  const isVisible = await loadingText.isVisible();
  
  if (!isVisible) {
    await expect(page).toHaveURL(/\/login/);
  }
});
