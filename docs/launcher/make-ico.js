// Convert DSH whale SVG to ICO (256x256 PNG-compressed entry) using sharp
const fs = require('fs');
const sharp = require('C:/Users/wangh/.dsh/profiles/node_modules/sharp');

(async () => {
  const svg = fs.readFileSync('G:/dsh/_tools/launcher/whale.svg');
  const png = await sharp(svg, { density: 600 })
    .resize(256, 256)
    .png()
    .toBuffer();

  // ICO container with a single 256x256 PNG entry (per ICO spec, width/height 0 means 256)
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); // reserved
  header.writeUInt16LE(1, 2); // type: icon
  header.writeUInt16LE(1, 4); // count
  const entry = Buffer.alloc(16);
  entry.writeUInt8(0, 0);     // width (0 = 256)
  entry.writeUInt8(0, 1);     // height (0 = 256)
  entry.writeUInt8(0, 2);     // color count
  entry.writeUInt8(0, 3);     // reserved
  entry.writeUInt16LE(1, 4);  // planes
  entry.writeUInt16LE(32, 6); // bit count
  entry.writeUInt32LE(png.length, 8);   // bytes in resource
  entry.writeUInt32LE(22, 12);          // offset
  const ico = Buffer.concat([header, entry, png]);
  fs.writeFileSync('G:/dsh/_tools/launcher/whale.ico', ico);
  fs.writeFileSync('G:/dsh/_tools/launcher/whale-256.png', png);
  console.log('ICO written:', ico.length, 'bytes (PNG payload', png.length + ')');
})();
