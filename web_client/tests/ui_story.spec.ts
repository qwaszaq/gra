import { test, expect } from '@playwright/test'

const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Story Mode Single Player', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SoloStory')
  await page.getByTestId('session-id').fill('ui-story-1')
  await page.getByTestId('connect-btn').click()
  await page.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await page.getByTestId('send-btn').click()
  
  // czekamy na obraz albo sam tekst
  await expect(page.locator('.narration-text')).toContainText(/./, { timeout: 30000 })
  
  // podszepty i HUD
  await expect(page.getByTestId('whispers-list')).toBeVisible()
  await expect(page.getByTestId('m-time')).toBeVisible()
})
