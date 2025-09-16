import { test, expect } from '@playwright/test'

const WS_URL = process.env.WS_URL || 'ws://localhost:65432/ws'

test('UI Debug WebSocket Messages', async ({ page }) => {
  // Intercept WebSocket messages
  await page.addInitScript(() => {
    const originalWebSocket = window.WebSocket;
    window.WebSocket = class extends WebSocket {
      constructor(url: string, protocols?: string | string[]) {
        super(url, protocols);
        console.log('WebSocket created:', url);
        
        this.addEventListener('message', (event) => {
          console.log('WebSocket message received:', event.data);
          try {
            const data = JSON.parse(event.data);
            console.log('Parsed message type:', data.type);
            if (data.type === 'narrative_update') {
              console.log('NARRATIVE UPDATE RECEIVED!');
              console.log('  Text:', data.text?.slice(0, 50) + '...');
              console.log('  Image:', data.image);
              console.log('  Voice:', data.voice_audio);
              console.log('  Music:', data.music);
            }
          } catch (e) {
            console.log('Failed to parse WebSocket message:', e);
          }
        });
        
        this.addEventListener('open', () => {
          console.log('WebSocket connection opened');
        });
        
        this.addEventListener('close', () => {
          console.log('WebSocket connection closed');
        });
      }
    };
  });

  await page.goto('/');

  // Wypełnij formularz
  await page.getByTestId('ws-url').fill(WS_URL);
  await page.getByTestId('player').fill('DebugTest');
  await page.getByTestId('session-id').fill('debug-test');

  // Upewnij się, że Single Player jest włączony
  const spCheckbox = page.getByTestId('single-player-checkbox');
  if (!(await spCheckbox.isChecked())) {
    await spCheckbox.check();
  }

  // Połącz
  await page.getByTestId('connect-btn').click();
  console.log('Connection button clicked');
  await page.waitForTimeout(2000);

  // Wyślij akcję
  await page.getByTestId('action-input').fill('Debug test action');
  await page.getByTestId('send-btn').click();
  console.log('Action sent');

  // Czekaj długo na WebSocket messages
  await page.waitForTimeout(15000);
  
  // Sprawdź stan UI
  const hasImg = await page.locator('.image img').count() > 0;
  const hasPlaceholder = await page.locator('.image .placeholder').count() > 0;
  
  console.log(`Final state - Has img: ${hasImg}, Has placeholder: ${hasPlaceholder}`);
  
  if (hasImg) {
    const imgSrc = await page.locator('.image img').getAttribute('src');
    console.log(`Image src: ${imgSrc}`);
  }
  
  // Test zawsze przechodzi - to jest debug test
  expect(true).toBeTruthy();
});
