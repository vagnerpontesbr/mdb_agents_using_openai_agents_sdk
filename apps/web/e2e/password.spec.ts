import { expect, test } from '@playwright/test';

test('password change clears secrets and requires fresh login while invalidating the old cookie', async ({page, context, baseURL}) => {
  await context.addCookies([{name:'telecom_session',value:'p'.repeat(43),url:baseURL!,httpOnly:true,sameSite:'Strict'}]);
  await page.goto('/#/profile');
  await expect(page.getByLabel('Current password')).toBeVisible();
  await page.getByLabel('Current password').fill('wrong-password');
  await page.getByLabel('New password', {exact:true}).fill('synthetic-password-after');
  await page.getByLabel('Confirm new password').fill('synthetic-password-after');
  await page.getByRole('button',{name:'Change password',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Check your current password');
  await expect(page.getByLabel('Current password')).toHaveValue('');
  await expect(page.getByLabel('New password',{exact:true})).toHaveValue('');
  await page.getByLabel('Current password').fill('synthetic-password-before');
  await page.getByLabel('New password',{exact:true}).fill('synthetic-password-after');
  await page.getByLabel('Confirm new password').fill('synthetic-password-after');
  await page.getByRole('button',{name:'Change password',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Sign in',exact:true})).toBeVisible();
  await expect(page.getByRole('status')).toHaveText('Password changed. Sign in with your new password.');
  expect(await page.evaluate(() => JSON.stringify([localStorage,sessionStorage]))).not.toContain('synthetic-password');
  const stale = await context.request.get('/api/me',{headers:{Cookie:'telecom_session='+'p'.repeat(43)}});
  expect(stale.status()).toBe(401);
  await page.getByLabel('Email',{exact:true}).fill('password-probe@example.test');
  await page.getByLabel('Password',{exact:true}).fill('synthetic-password-after');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByRole('heading',{name:'My profile',exact:true})).toBeVisible();
  await expect(page.getByLabel('Current password')).toHaveValue('');
});
