import { test, expect } from '@playwright/test'

const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Two-gear Image Swap', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SwapUI')
  await page.getByTestId('session-id').fill('ui-swap-1')
  await page.getByTestId('connect-btn').click()
  await page.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await page.getByTestId('send-btn').click()

  const img = page.locator('.scene-image img')
  await expect(img).toBeVisible({ timeout: 30000 })
  const firstSrc = await img.getAttribute('src')
  expect(firstSrc).toBeTruthy()

  // Czekaj na swap (src zmieni się na generated)
  await page.waitForFunction(() => {
    const el = document.querySelector('.scene-image img') as HTMLImageElement | null
    return el && /generated\/.+\.png/.test(el.src)
  }, null, { timeout: 60000 })
  const finalSrc = await img.getAttribute('src')
  expect(finalSrc).not.toEqual(firstSrc)
})
