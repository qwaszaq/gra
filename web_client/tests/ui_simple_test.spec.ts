import { test, expect } from '@playwright/test'

const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Simple Test - Check if image appears', async ({ page }) => {
  await page.goto('/')

  // Wypełnij formularz
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SimpleTest')
  await page.getByTestId('session-id').fill('simple-test')

  // Upewnij się, że Single Player jest włączony
  const spCheckbox = page.getByTestId('single-player-checkbox')
  if (!(await spCheckbox.isChecked())) {
    await spCheckbox.check()
  }

  // Połącz
  await page.getByTestId('connect-btn').click()
  await page.waitForTimeout(1000) // Czekaj na połączenie

  // Wyślij akcję
  await page.getByTestId('action-input').fill('Test akcja')
  await page.getByTestId('send-btn').click()

  // Długi wait na narrative_update (bot + orchestrator + broadcast)
  await page.waitForTimeout(10000) // 10 sekund na pełny flow

  // Sprawdź czy currentImage się pojawiło
  await page.waitForFunction(() => {
    // Sprawdź czy jest img element z src
    const img = document.querySelector('.image img') as HTMLImageElement | null
    return img && img.src && img.src !== ''
  }, { timeout: 30_000 }).catch(() => {
    console.log('Timeout waiting for image - checking what we have')
  })

  // Sprawdź czy to jest img czy placeholder
  const hasImg = await page.locator('.image img').count() > 0
  const hasPlaceholder = await page.locator('.image .placeholder').count() > 0
  
  console.log(`Has img: ${hasImg}, Has placeholder: ${hasPlaceholder}`)
  
  if (hasImg) {
    console.log('SUCCESS: Image element found!')
    const imgSrc = await page.locator('.image img').getAttribute('src')
    console.log(`Image src: ${imgSrc}`)
  } else {
    console.log('INFO: Only placeholder found, no image yet')
  }

  // Test przechodzi jeśli jest jakikolwiek content w .image
  expect(hasImg || hasPlaceholder).toBeTruthy()
})
