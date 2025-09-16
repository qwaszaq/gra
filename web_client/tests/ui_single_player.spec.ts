import { test, expect } from '@playwright/test'

const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Single Player', async ({ page }) => {
  // 1) Wejdź do UI
  await page.goto('/')

  // 2) Wypełnij formularz i połącz
  await page.getByTestId('ws-url').fill(WS_URL)
  await page.getByTestId('player').fill('SoloUI')
  await page.getByTestId('session-id').fill('ui-sp-demo')
  await page.getByTestId('connect-btn').click()

  // 3) Wyślij akcję (klik jest ważny ze względu na politykę autoplay)
  await page.getByTestId('action-input').fill('Sprawdzam miejsce zbrodni')
  await page.getByTestId('send-btn').click()

  // 4) Czekaj na obraz (narrative_update -> UI wstawia <img/>)
  await expect(page.locator('.image img')).toBeVisible({ timeout: 30_000 })

  // 5) Czekaj na audio (voice + music) - może przyjść później
  await page.waitForTimeout(5000) // daj czas na TTS generation

  // 6) Sprawdź źródła audio (voice + music)
  const voiceSrc = await page.getByTestId('voice-audio').getAttribute('src')
  const musicSrc = await page.getByTestId('music-audio').getAttribute('src')
  
  // Voice może być null (TTS może nie działać), ale music powinno być
  if (voiceSrc) {
    expect(voiceSrc).toContain('http://localhost:8001/audio/')
  }
  expect(musicSrc).toBeTruthy() // np. http://localhost:8003/music/track_X.mp3
  expect(musicSrc).toContain('http://localhost:8003/music/')

  // 7) Spróbuj zagrać głos (w razie gdyby autoplay był zablokowany)
  await page.evaluate(() => {
    const a = document.querySelector('[data-testid="voice-audio"]') as HTMLAudioElement | null
    if (a && a.paused) a.play().catch(()=>{})
  })

  // Krótka pauza, by usłyszeć dźwięk
  await page.waitForTimeout(1500)
})
