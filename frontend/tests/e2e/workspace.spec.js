import { test, expect } from "@playwright/test";
import fs from "node:fs";
const demo = JSON.parse(fs.readFileSync("../.local/demo-account.json", "utf8"));
const ids = JSON.parse(fs.readFileSync("../.local/demo-projects.json", "utf8"));
const savedDiagrams = JSON.parse(fs.readFileSync("tests/fixtures/saved-diagrams.json", "utf8"));
let sessionCookies;
test.beforeEach(async ({ page }) => {
  if (sessionCookies) {
    await page.context().addCookies(sessionCookies);
    await page.goto('/');
    await expect(page.getByRole('heading', {name:/Hello, Student/})).toBeVisible();
    return;
  }
  await page.goto("/");
  await page.getByLabel("Email address").fill(demo.email);
  await page.getByLabel("Password", { exact: true }).fill(demo.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: /Hello, Student/ }),
  ).toBeVisible();
  sessionCookies = await page.context().cookies();
});
test("desktop dashboard and every workspace tab", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.screenshot({
    path: "../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: /URL Shortener FastAPI/ }).click();
  await expect(
    page.getByRole("heading", { name: "URL Shortener", exact: true }),
  ).toBeVisible();
  for (const name of [
    "Requirements",
    "Architecture",
    "Database and APIs",
    "Code",
    "Code Review",
    "Testing",
    "Documentation",
    "Overview",
  ]) {
    await page.getByRole("tab", { name, exact: true }).click();
    await expect(page.getByRole("tab", { name, exact: true })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  }
  await page.screenshot({
    path: "../docs/screenshots/workspace.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
test("imported files require approval and code editor can compare", async ({
  page,
}) => {
  const request=page.request;
  const me = await request.get('/api/auth/me');
  const { csrf_token } = await me.json();
  const headers = { "X-CSRF-Token": csrf_token };
  const p = await request.post("/api/projects", {
    headers,
    data: {
      project_name: "UI file approval " + Date.now(),
      description:
        "An automated UI verification workspace for source import and version comparison.",
      programming_language: "Python",
      framework: "FastAPI",
      application_type: "library",
    },
  });
  expect(p.status()).toBe(201);
  const project = await p.json();
  await page.goto("/projects/" + project.id);
  await page.getByRole("tab", { name: "Code", exact: true }).click();
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "calculator.py",
      mimeType: "text/plain",
      buffer: Buffer.from("def add(a, b):\n    return a + b\n"),
    });
  await expect(
    page.getByRole("heading", { name: "Code is ready to review" }),
  ).toBeVisible();
  await expect(page.getByText("A clean slate")).toBeVisible();
  await page.getByRole("button", { name: "Approve and continue" }).click();
  await expect(
    page.locator(".file-tree").getByText("calculator.py"),
  ).toBeVisible();
  await expect(page.locator(".monaco-editor").first()).toBeVisible();
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await expect(page.locator(".monaco-diff-editor")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/code-editor.png",
    fullPage: true,
  });
  await page.getByRole('button', {name:'Dark mode',exact:true}).click();
  await expect(page.locator('.monaco-editor.vs-dark').first()).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/editorial-code-dark.png',fullPage:true});
  const removed = await request.delete('/api/projects/' + project.id, {headers,params:{confirm_name:project.project_name}});
  expect(removed.ok()).toBe(true);
});
test("mobile navigation and settings are usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your workspace settings" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
});

test('approved architecture diagrams render and Swagger loads', async ({page}) => {
  await page.goto('/projects/' + ids['URL Shortener']);
  await page.getByRole('tab', {name:'Architecture',exact:true}).click();
  for (const name of ['Component Flowchart','Request Sequence Diagram','Domain Class Diagram']) {
    const block=page.locator('.diagram-block').filter({has:page.getByRole('heading',{name,exact:true})});
    await expect(block.locator('.diagram > svg')).toHaveCount(1,{timeout:20000});
  }
  await expect(page.getByText('Diagram could not be rendered.',{exact:false})).toHaveCount(0);
  await page.screenshot({path:'../docs/screenshots/architecture.png',fullPage:true});
  await page.goto('/docs');
  await expect(page.locator('.swagger-ui .info .title')).toContainText('DevSphere AI',{timeout:30000});
  await expect(page.getByRole('button',{name:'Authorize',exact:false}).first()).toBeVisible();
});

test('all saved diagrams render, including colon-style ER attributes, in light and dark themes', async ({page}) => {
  const path = '/api/projects/' + ids['URL Shortener'] + '/documents';
  await page.route('**' + path, async route => {
    const response = await route.fetch();
    const documents = await response.json();
    for (const document of documents) {
      if (document.document_type === 'architecture')
        document.document_content.diagrams = savedDiagrams.map(d => ({title:d.name, mermaid:d.source}));
    }
    await route.fulfill({response, json:documents});
  });
  await page.goto('/projects/' + ids['URL Shortener']);
  await page.getByRole('tab', {name:'Architecture',exact:true}).click();
  await expect(page.locator('.diagram > svg')).toHaveCount(savedDiagrams.length);
  await expect(page.locator('.error-icon, .error-text')).toHaveCount(0);
  const erBlock = page.locator('.diagram-block').filter({hasText:'Saved database diagram 12'});
  await expect(erBlock.locator('.diagram')).toContainText('UUID');
  await erBlock.screenshot({path:'../docs/screenshots/ui-refresh-er-light.png'});
  await page.screenshot({path:'../docs/screenshots/ui-refresh-diagrams-light.png',fullPage:true});
  const firstId = await page.locator('.diagram > svg').first().getAttribute('id');
  await page.getByRole('button', {name:'Dark mode',exact:true}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.locator('.diagram > svg').first()).not.toHaveAttribute('id',firstId);
  await expect(page.locator('.diagram > svg')).toHaveCount(savedDiagrams.length);
  const erColors = await erBlock.locator('.diagram svg').evaluate(svg => ({
    text: Array.from(svg.querySelectorAll('text')).filter(t => t.textContent.includes('UUID')).map(t => getComputedStyle(t).fill),
    rows: Array.from(svg.querySelectorAll('.row-rect-odd path, .row-rect-even path')).map(r => getComputedStyle(r).fill).filter(c => c !== 'none'),
  }));
  expect(erColors.text.length).toBeGreaterThan(0);
  expect(erColors.rows.length).toBeGreaterThan(0);
  // Mermaid's default white attribute rows made light text illegible in dark mode.
  const luminance = color => {
    const [r,g,b] = color.match(/[\d.]+/g).slice(0,3).map(Number).map(v => {
      const c=v/255; return c<=0.04045 ? c/12.92 : ((c+0.055)/1.055)**2.4;
    });
    return 0.2126*r+0.7152*g+0.0722*b;
  };
  for (const foreground of erColors.text) for (const background of erColors.rows) {
    const a=luminance(foreground), b=luminance(background);
    expect((Math.max(a,b)+0.05)/(Math.min(a,b)+0.05)).toBeGreaterThanOrEqual(4.5);
  }
  await erBlock.screenshot({path:'../docs/screenshots/ui-refresh-er-dark.png'});
  await expect(page.locator('.error-icon, .error-text')).toHaveCount(0);
  await page.screenshot({path:'../docs/screenshots/ui-refresh-diagrams-dark.png',fullPage:true});
  await page.getByRole('button', {name:'Light mode',exact:true}).click();
});

test('unrepairable diagrams show one inline notice and leave no Mermaid error SVG after navigation', async ({page}) => {
  const path = '/api/projects/' + ids['URL Shortener'] + '/documents';
  await page.route('**' + path, async route => {
    const response = await route.fetch(); const documents = await response.json();
    for (const d of documents) if (d.document_type === 'architecture')
      d.document_content.diagrams = [{title:'Invalid test fixture',mermaid:'erDiagram\nUser {\n ???\n }'}];
    await route.fulfill({response,json:documents});
  });
  await page.goto('/projects/' + ids['URL Shortener']);
  await page.getByRole('tab', {name:'Architecture',exact:true}).click();
  await expect(page.getByText(/This diagram needs a syntax correction/)).toHaveCount(1);
  await expect(page.locator('.error-icon, .error-text, .diagram-render-buffer')).toHaveCount(0);
  await page.getByRole('tab', {name:'Overview',exact:true}).click();
  await expect(page.getByText(/This diagram needs a syntax correction/)).toHaveCount(0);
  await expect(page.locator('.error-icon, .error-text, .diagram-render-buffer')).toHaveCount(0);
});

test('completed workflows stop polling and refresh only on demand', async ({page}) => {
  let reads = 0;
  page.on('request', request => {if (request.url().endsWith('/workflow')) reads++;});
  await page.goto('/projects/' + ids['URL Shortener']);
  await expect(page.locator('.live-indicator')).toHaveText('Completed');
  await expect(page.getByRole('button',{name:'Cancel workflow'})).toHaveCount(0);
  const settled = reads;
  await page.waitForTimeout(4500);
  expect(reads).toBe(settled);
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await expect.poll(() => reads).toBeGreaterThan(settled);
  await expect(page.locator('.live-indicator')).toHaveText('Completed');
});

test('new palette is responsive and dark theme persists after reload', async ({page}) => {
  await expect(page.getByRole('link', {name:/URL Shortener FastAPI/})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/editorial-dashboard.png',fullPage:true});
  await page.getByRole('button',{name:'Dark mode',exact:true}).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.getByRole('link', {name:/URL Shortener FastAPI/})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/editorial-dashboard-dark.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('heading',{name:/Hello, Student/})).toBeVisible();
  await expect.poll(() => page.locator('.sidebar').evaluate(el => el.getBoundingClientRect().right)).toBeLessThanOrEqual(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path:'../docs/screenshots/editorial-mobile.png',fullPage:true});
  await page.getByRole('button', {name:'Toggle navigation',exact:true}).click();
  await expect(page.getByRole('button', {name:'Toggle navigation',exact:true})).toHaveAttribute('aria-expanded','true');
  await page.getByRole('button', {name:'Close navigation',exact:true}).click({position:{x:370,y:500}});
  await expect(page.getByRole('button', {name:'Toggle navigation',exact:true})).toHaveAttribute('aria-expanded','false');
  await page.setViewportSize({width:1440,height:980});
  await page.getByRole('button', {name:'Light mode',exact:true}).click();
  await page.goto('/new');
  await expect(page.locator('.project-form')).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/editorial-new-project.png',fullPage:true});
  await page.getByRole('button', {name:'Sign out',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Welcome back',exact:true})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/editorial-sign-in.png',fullPage:true});
});

for (const mode of ['paste','upload']) test(`code review accepts ${mode} input and saves the exact initial source`,async({page})=>{
  // This browser contract check avoids a real model call; live model evidence is recorded separately.
  let submitted;
  await page.route('**/api/projects/*/execute',async route=>{
    submitted=route.request().postDataJSON();
    await route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({run_id:'browser-test-only',status:'queued',status_url:'/not-used'})});
  });
  await page.goto('/review');
  await expect(page.getByRole('heading',{name:'Find the bug. See the fix.'})).toBeVisible();
  const source='function add(a,b) { return a-b; }\n';
  await page.getByLabel('Review name',{exact:false}).fill('UI '+mode+' review '+Date.now());
  if(mode==='paste') {
    await page.getByLabel('Filename',{exact:true}).fill('calculator.js');
    await page.getByLabel('Source code',{exact:true}).fill(source);
  } else {
    await page.getByRole('tab',{name:'Upload files',exact:true}).click();
    await page.getByLabel('Choose source files',{exact:true}).setInputFiles({name:'calculator.js',mimeType:'text/javascript',buffer:Buffer.from(source)});
    await expect(page.getByText('calculator.js',{exact:true})).toBeVisible();
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({path:'../docs/screenshots/review-upload.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await expect.poll(()=>page.locator('.sidebar').evaluate(el=>el.getBoundingClientRect().right)).toBeLessThanOrEqual(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:'../docs/screenshots/review-mobile.png',fullPage:true});
  }
  await page.getByRole('button',{name:'Save & review code'}).click();
  await page.waitForURL('**/projects/*');
  await expect(page.getByRole('tab',{name:'Code Review',exact:true})).toHaveAttribute('aria-selected','true');
  expect(submitted.workflow_type).toBe('quick_review');
  const id=page.url().split('/').pop();
  const stored=await (await page.request.get(`/api/projects/${id}/files`)).json();
  expect(stored[0].file_content).toBe(source);
  const project=await (await page.request.get(`/api/projects/${id}`)).json();
  const {csrf_token}=await (await page.request.get('/api/auth/me')).json();
  expect((await page.request.delete(`/api/projects/${id}`,{headers:{'X-CSRF-Token':csrf_token},params:{confirm_name:project.project_name}})).ok()).toBe(true);
});

test('recorded code reviews show source context and replacement suggestions',async({page})=>{
  await page.goto('/projects/'+ids['Node Code Review']);
  await page.getByRole('tab',{name:'Code Review',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Suggested replacement code'}).first()).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy code'}).first()).toBeVisible();
  await page.getByText('Source context',{exact:true}).first().click();
  await page.screenshot({path:'../docs/screenshots/review-suggestions.png',fullPage:true});
});
