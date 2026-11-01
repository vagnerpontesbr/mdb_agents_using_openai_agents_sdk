import { expect, test } from '@playwright/test';

test('profile persists name, timezone and language through reload and login; stale changes are rejected', async ({ page }) => {
  await page.goto('/#/profile');
  await page.getByLabel('Email', { exact: true }).fill('admin@mongodb.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-only');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByLabel('Display name')).toBeVisible();
  await page.getByLabel('Display name').fill('Synthetic Administrator');
  await page.getByLabel('Timezone').fill('America/Sao_Paulo');
  await page.getByRole('combobox', {name:'Language', exact:true}).selectOption('pt-BR');
  await page.getByRole('button', { name: 'Save profile', exact: true }).click();
  await expect(page.getByRole('status')).toHaveText('Perfil salvo.');
  await expect(page.locator('html')).toHaveAttribute('lang', 'pt-BR');
  await page.reload();
  await expect(page.getByLabel('Nome de exibição')).toHaveValue('Synthetic Administrator');
  await expect(page.getByLabel('Fuso horário')).toHaveValue('America/Sao_Paulo');
  const saved = await page.evaluate(async () => (await fetch('/api/profile')).json());
  expect(saved.locale).toBe('pt-BR');
  await page.evaluate(async profile => {
    await fetch('/api/profile', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({
      display_name: 'Other tab', timezone: profile.timezone, locale: profile.locale, expected_revision: profile.revision,
    }) });
  }, saved);
  await page.getByLabel('Nome de exibição').fill('Stale value');
  await page.getByRole('button', {name:'Salvar perfil',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('O perfil mudou');
  await page.getByRole('button', {name:'Recarregar perfil'}).click();
  await expect(page.getByLabel('Nome de exibição')).toHaveValue('Other tab');
  await page.getByRole('button', {name:'Perfil',exact:true}).click();
  await page.getByRole('button', {name:'Sair',exact:true}).click();
  await page.getByLabel('E-mail', {exact:true}).fill('admin@mongodb.com');
  await page.getByLabel('Senha', {exact:true}).fill('synthetic-browser-only');
  await page.getByRole('button', {name:'Entrar',exact:true}).click();
  await expect(page.getByLabel('Nome de exibição')).toHaveValue('Other tab');
  // Restore the synthetic fixture preference so other legacy suites remain independent.
  await page.getByRole('combobox', {name:'Idioma', exact:true}).selectOption('en-US');
  await page.getByRole('button', {name:'Salvar perfil',exact:true}).click();
  await expect(page.getByRole('status')).toHaveText('Profile saved.');
});

test('inline language changes preserve a running conversation and its original result', async ({ page }) => {
  const user = { user_id: 'locale-synthetic', email: 'locale@example.test', role: 'user' };
  let profile = { ...user, display_name: 'Synthetic User', timezone: 'UTC', locale: 'en-US', revision: 0 };
  await page.route('**/api/me', r => r.fulfill({json:user}));
  await page.route('**/api/profile', r => {
    if (r.request().method() === 'POST') {
      const data = r.request().postDataJSON();
      expect(data.expected_revision).toBe(profile.revision);
      profile = {...profile, locale: data.locale, revision: profile.revision + 1};
    }
    return r.fulfill({json:profile});
  });
  await page.route('**/api/capabilities', r => r.fulfill({json:{journey:true,voice:true,knowledge:false}}));
  await page.route('**/api/journey/latest', r => r.fulfill({json:{status:'empty'}}));
  await page.goto('/');
  await expect(page.getByLabel('Your message')).toBeEnabled();
  const id = await page.evaluate(() => sessionStorage.getItem('telecom-conversation-locale-synthetic'));
  await page.getByLabel('Your message').fill('Original question');
  let release!: () => void;
  const held = new Promise<void>(resolve => {release=resolve;});
  let calls=0;
  await page.route('**/api/journey/chat', async r => {
    calls++; await held;
    await r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: {"execution_id":"00000000-0000-4000-8000-000000000007","status":"completed","text":"Original English response"}\n\n'});
  });
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(() => calls).toBe(1);
  await page.getByRole('button',{name:'Profile',exact:true}).click();
  await page.getByRole('combobox', {name:'Language', exact:true}).selectOption('pt-BR');
  await expect(page.getByRole('button',{name:'Perfil',exact:true})).toBeVisible();
  await page.getByRole('combobox', {name:'Idioma', exact:true}).selectOption('es-ES');
  await expect(page.getByLabel('Tu mensaje')).toBeVisible();
  release();
  await expect(page.locator('.result')).toHaveText('Original English response');
  await expect(page.locator('.result')).toHaveAttribute('lang', 'en-US');
  await expect(page.locator('.response-language')).toHaveText('Idioma de la respuesta: Inglés');
  expect(calls).toBe(1);
  expect(await page.evaluate(() => sessionStorage.getItem('telecom-conversation-locale-synthetic'))).toBe(id);
  await page.evaluate(() => {
    document.documentElement.dataset.pauses = '0';
    HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };
    HTMLMediaElement.prototype.pause = function () {
      document.documentElement.dataset.pauses = String(Number(document.documentElement.dataset.pauses) + 1);
    };
  });
  await page.route('**/api/voice/speak', r => r.fulfill({contentType:'audio/wav',body:Buffer.from('synthetic lifecycle double')}));
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Escuchar respuesta',exact:true}).click();
  await expect(page.getByRole('button',{name:'Escuchar respuesta',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Perfil',exact:true}).click();
  await page.getByRole('combobox',{name:'Idioma',exact:true}).selectOption('en-US');
  await expect(page.getByRole('button',{name:'Profile',exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.dataset.pauses)).toBe('0');
  await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('es-ES');
  await expect(page.getByLabel('Tu mensaje')).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/profile-spanish-mobile.png',fullPage:true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
