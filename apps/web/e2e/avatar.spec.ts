import { expect, test } from '@playwright/test';

// Generated synthetic raster; no personal image or retained original upload.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aV1sAAAAASUVORK5CYII=', 'base64');

test('own photo add, reload, replacement and removal use normalized private images', async ({ page }) => {
  await page.goto('/#/profile');
  await page.getByLabel('Email', {exact:true}).fill('admin@mongodb.com');
  await page.getByLabel('Password', {exact:true}).fill('synthetic-browser-only');
  await page.getByRole('button', {name:'Sign in',exact:true}).click();
  await expect(page.getByRole('img', {name:'Profile initials'})).toBeVisible();
  // Generate PNG through the browser so its CRCs are valid for the decoder.
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width=12; canvas.height=8;
    const context=canvas.getContext('2d')!; context.fillStyle='#007453'; context.fillRect(0,0,12,8);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  const file = {name:'synthetic.png',mimeType:'image/png',buffer:Buffer.from(encoded,'base64')};
  await page.getByLabel('Choose photo').setInputFiles(file);
  await expect(page.getByRole('status')).toHaveText('Photo saved.');
  const image=page.getByRole('img',{name:'Your profile photo'});
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(12);
  await page.reload();
  await expect(image).toBeVisible();
  await page.getByLabel('Choose photo').setInputFiles(file);
  await expect(page.getByRole('status')).toHaveText('Photo saved.');
  await page.getByRole('button',{name:'Remove photo'}).click();
  await expect(page.getByRole('status')).toHaveText('Photo removed.');
  await expect(page.getByRole('img',{name:'Profile initials'})).toBeVisible();
  await page.getByLabel('Choose photo').setInputFiles({name:'unsafe.svg',mimeType:'image/svg+xml',buffer:Buffer.from('<svg/>')});
  await expect(page.getByRole('status')).toHaveText('Choose a JPEG or PNG up to 2 MiB.');
  await page.getByLabel('Choose photo').setInputFiles({name:'invalid.png',mimeType:'image/png',buffer:png.subarray(0,20)});
  await expect(page.getByRole('status')).toHaveText('Choose a valid JPEG or PNG within the image limits.');
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/avatar-mobile.png',fullPage:true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
