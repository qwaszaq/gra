import { test, expect } from '@playwright/test'
const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Story Shot & Swap', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('ShotUI')
  await page.getByTestId('session-id').fill('ui-shot-1')
  await page.getByTestId('connect-btn').click()
  await page.getByTestId('action-input').fill('Przesłuchuję świadka')
  await page.getByTestId('send-btn').click()

  const img = page.locator('.scene-image img')
  await expect(img).toBeVisible({ timeout: 30000 })
  await expect(page.locator('.shot-badge')).toBeVisible()

  // poczekaj na swap na generated (jak w poprzednim teście)
  await page.waitForFunction(() => {
    const el = document.querySelector('.scene-image img') as HTMLImageElement | null
    return el && /generated\/.+\.png/.test(el.src)
  }, null, { timeout: 60000 })
})
