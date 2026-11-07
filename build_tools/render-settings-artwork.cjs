// Development-only: npm install --prefix ../tmp/artwork sharp, then expose NODE_PATH.
// Checked-in PNGs keep SVG rendering libraries out of the appliance runtime.
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '../zmala_terminal/common/assets/settings');
async function render(directory) {
  for (const entry of await fs.readdir(directory, {withFileTypes:true})) {
    const source = path.join(directory, entry.name);
    if (entry.isDirectory()) await render(source);
    else if (entry.name.endsWith('.svg')) {
      await sharp(source).resize({width:256}).png().toFile(source.replace(/\.svg$/, '.png'));
    }
  }
}
render(root).catch(error => { console.error(error); process.exitCode=1; });
