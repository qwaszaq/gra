import { test, expect } from '@playwright/test'
const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('Guardrails Noir: off-domain input gets reframed', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('GuardUI')
  await page.getByTestId('session-id').fill('ui-guard-1')
  await page.getByTestId('connect-btn').click()

  await page.getByTestId('action-input').fill('sadzę ogórki i hoduję ślimaki')
  await page.getByTestId('send-btn').click()

  // Dostajemy scenę (nie error), z banerem reframe i obrazem
  await expect(page.locator('.narration-text')).toContainText(/./, { timeout: 30000 })
  await expect(page.locator('text=Zreinterpretowano wejście')).toBeVisible()
  const img = page.locator('.image img')
  await expect(img).toBeVisible({ timeout: 30000 })
  const voiceSrc = await page.getByTestId('voice-audio').getAttribute('src')
  expect(voiceSrc).toBeTruthy()
})
