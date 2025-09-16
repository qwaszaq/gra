import { test, expect } from '@playwright/test'

const WS_URL      = process.env.WS_URL      || 'ws://localhost:65432/ws'
const ADMIN_BASE  = process.env.ADMIN_BASE  || 'http://localhost:8002'
const GS_BASE     = process.env.GS_BASE     || 'http://localhost:65432'
const VISION_BASE = process.env.VISION_BASE || process.env.VITE_VISION_BASE || 'http://localhost:8004'
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'dev_admin_token_123'

// Pomocnik: sprawdza, że URL zwraca HTTP 200
async function expect200(page: any, url?: string | null) {
  expect(url, 'URL is missing').toBeTruthy()
  const resp = await page.request.get(url!)
  expect(resp.status(), `GET ${url} not 200`).toBe(200)
}

// 1) Single Player – „jak gra"
test('UI Single Player', async ({ page }) => {
  await page.goto('/')

  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SoloUI')
  await page.getByTestId('session-id').fill('ui-sp-demo')

  // Upewnij się, że Single Player jest włączony
  const spCheckbox = page.getByTestId('single-player-checkbox')
  await expect(spCheckbox).toBeVisible()
  const checked = await spCheckbox.isChecked()
  if (!checked) await spCheckbox.check()
  console.log(`Single Player checkbox checked: ${checked}`)

  await page.getByTestId('connect-btn').click()

  // Klik (ważny dla autoplay) i wysyłamy jedną akcję
  await page.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await page.getByTestId('send-btn').click()

  // Obraz – wyświetlony w UI, czekaj na src (narrative_update)
  const img = page.locator('.image img')
  await expect(img).toBeVisible({ timeout: 30_000 })
  
  // Czekaj aż obraz będzie miał src (narrative_update processed) - może trwać ~10s
  await page.waitForFunction(() => {
    const imgEl = document.querySelector('.image img') as HTMLImageElement | null
    return imgEl && imgEl.src && imgEl.src !== ''
  }, { timeout: 45_000 })

  // Pobierz src i sprawdź 200 (nie placeholder)
  const imgSrc = await img.getAttribute('src')
  expect(imgSrc, 'image src missing').toBeTruthy()
  expect(imgSrc!.includes('placeholder')).toBeFalsy()
  await expect200(page, imgSrc)

  // TTS – voice audio ma src i 200 (czekaj na narrative_update)
  await page.waitForFunction(() => {
    const voiceEl = document.querySelector('[data-testid="voice-audio"]') as HTMLAudioElement | null
    return voiceEl && voiceEl.src && voiceEl.src !== ''
  }, { timeout: 30_000 })
  
  const voiceSrc = await page.getByTestId('voice-audio').getAttribute('src')
  await expect200(page, voiceSrc)

  // Wymuś play (gdyby autoplay był zablokowany)
  await page.evaluate(() => {
    const a = document.querySelector('[data-testid="voice-audio"]') as HTMLAudioElement | null
    if (a && a.paused) a.play().catch(()=>{})
  })

  // Muzyka – ma src i 200 (Suno/fallback)
  await page.waitForFunction(() => {
    const musicEl = document.querySelector('[data-testid="music-audio"]') as HTMLAudioElement | null
    return musicEl && musicEl.src && musicEl.src !== ''
  }, { timeout: 30_000 })
  
  const musicSrc = await page.getByTestId('music-audio').getAttribute('src')
  await expect200(page, musicSrc)

  // Opcjonalnie – pokaż galerię Generated (jeśli przycisk jest)
  const toggleGallery = page.getByTestId('toggle-gallery')
  if (await toggleGallery.count()) {
    await toggleGallery.click()
    await page.waitForTimeout(1000)
  }
})

// 2) Multiplayer – broadcast do dwóch kart
test('UI Multiplayer', async ({ browser, baseURL }) => {
  // Karta 1
  const ctx1 = await browser.newContext()
  const p1 = await ctx1.newPage()
  await p1.goto(baseURL!)
  await p1.getByTestId('ws-url').fill(WS_URL)
  await p1.getByTestId('player').fill('Marlow')
  await p1.getByTestId('session-id').fill('ui-mp-demo')
  await p1.getByTestId('connect-btn').click()

  // Karta 2
  const ctx2 = await browser.newContext()
  const p2 = await ctx2.newPage()
  await p2.goto(baseURL!)
  await p2.getByTestId('ws-url').fill(WS_URL)
  await p2.getByTestId('player').fill('Spade')
  await p2.getByTestId('session-id').fill('ui-mp-demo')
  await p2.getByTestId('connect-btn').click()

  // Akcje – kolejność jest ważna
  await p1.getByTestId('action-input').fill('Przesłuchuję świadka')
  await p1.getByTestId('send-btn').click()
  await p2.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await p2.getByTestId('send-btn').click()

  // Zobacz obraz w p1
  const img1 = p1.locator('.image img')
  await expect(img1).toBeVisible({ timeout: 30_000 })
  await expect200(p1, await img1.getAttribute('src'))

  // I w p2 (broadcast)
  const img2 = p2.locator('.image img')
  await expect(img2).toBeVisible({ timeout: 30_000 })
  await expect200(p2, await img2.getAttribute('src'))

  await ctx1.close(); await ctx2.close()
})

// 3) Override – przez API i live update w UI
test('UI Override via API', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SoloOverride')
  await page.getByTestId('session-id').fill('ui-ov-demo')
  await page.getByTestId('connect-btn').click()

  // Jedna akcja – SP domknie turę
  await page.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await page.getByTestId('send-btn').click()
  await expect(page.locator('.image img')).toBeVisible({ timeout: 30_000 })

  // Wyślij override do Game Server (API)
  const newImage = `${VISION_BASE}/assets/images/case_zero/turn3.png`
  const res = await page.request.post(`${GS_BASE}/override`, {
    headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
    data: { session_id: 'ui-ov-demo', turn: 1, image: newImage }
  })
  expect(res.status()).toBe(200)

  // Czekamy na override_update w kliencie – obraz powinien się zmienić
  await page.waitForFunction(
    (expected) => {
      const img = document.querySelector('.image img') as HTMLImageElement | null
      return !!(img && img.getAttribute('src') === expected)
    },
    newImage,
    { timeout: 15_000 }
  )
  await expect200(page, newImage)
})
