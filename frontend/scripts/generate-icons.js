const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// SVG content for TT-Bot logo
const svgContent = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#CC785C;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#9E5A4A;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="100" fill="url(#grad)"/>
  <text x="256" y="268" font-family="Arial, sans-serif" font-size="280" font-weight="bold" text-anchor="middle" dominant-baseline="middle" fill="white">TT</text>
</svg>
`;

const sizes = [
  { size: 32, name: 'favicon-32x32.png' },
  { size: 16, name: 'favicon-16x16.png' },
  { size: 180, name: 'apple-icon.png' },
  { size: 192, name: 'icon-192.png' },
  { size: 512, name: 'icon-512.png' },
];

const appDir = path.join(__dirname, '../app');

async function generateIcons() {
  for (const { size, name } of sizes) {
    await sharp(Buffer.from(svgContent))
      .resize(size, size)
      .png()
      .toFile(path.join(appDir, name));
    console.log(`Generated ${name}`);
  }

  console.log('All icons generated successfully!');
  console.log('Note: favicon.ico not generated - using PNG/SVG instead (modern browsers support them)');
}

generateIcons().catch(console.error);
