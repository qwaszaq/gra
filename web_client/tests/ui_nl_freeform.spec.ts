import { test, expect } from '@playwright/test'
const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('Free-form NL: reload + cigarette + window', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('NL-UI')
  await page.getByTestId('session-id').fill('ui-nl-1')
  await page.getByTestId('single-player-checkbox').check()
  await page.getByTestId('connect-btn').click()

  await page.getByTestId('action-input').fill('Przeładowuję pistolet, zapalam papierosa i wyglądam przez okno.')
  await page.getByTestId('send-btn').click()

  await expect(page.locator('.narration-text')).toContainText(/./, { timeout: 30000 })
  await expect(page.locator('.image img')).toBeVisible({ timeout: 30000 })
  const voiceSrc = await page.getByTestId('voice-audio').getAttribute('src')
  expect(voiceSrc).toBeTruthy()

  // Sprawdź chipy inventory/location (mogą się różnić w zależności od modelu — patrzymy na obecność)
  await expect(page.locator('text=Magazynek')).toBeVisible()
  await expect(page.locator('text=📍')).toBeVisible()
})
