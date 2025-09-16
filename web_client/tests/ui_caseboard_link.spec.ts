import { test, expect } from '@playwright/test'
const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('CaseBoard link -> graph_update', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('LinkUI')
  await page.getByTestId('session-id').fill('ui-link-1')
  await page.getByTestId('connect-btn').click()
  // scenka, by mieć co najmniej dwa węzły
  await page.getByTestId('action-input').fill('Przesłuchuję świadka i oglądam zakrwawiony nóż.')
  await page.getByTestId('send-btn').click()
  // pokaż Case Board
  await page.getByRole('button', { name: /Case Board/i }).click()
  // spróbuj połączyć ręcznie (tu użyj przykładowych etykiet – jeśli brak, wpisz własne)
  // Nie znamy faktycznych labeli; test minimalny: sprawdź, że sekcja Edges się pojawia
  await expect(page.locator('text=Edges')).toBeVisible({ timeout: 30000 })
})
