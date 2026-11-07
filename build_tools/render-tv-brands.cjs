// Development-only; checked-in PNGs require no SVG library on the appliance.
const fs = require('node:fs/promises');
const path = require('node:path');
const sharp = require('sharp');
const root = path.resolve(__dirname, '../zmala_terminal/common/assets/tv-brands');
const colors = {samsung:'#1428a0', sony:'#000000', lg:'#a50034', toshiba:'#ff0000', panasonic:'#0049ab'};
async function render() {
  for (const file of await fs.readdir(root)) {
    if (!file.endsWith('.svg')) continue;
    const name = file.slice(0, -4);
    let source = await fs.readFile(path.join(root, file), 'utf8');
    if (colors[name]) source = source.replace('<svg ', `<svg fill="${colors[name]}" `);
    const trimmed = await sharp(Buffer.from(source), {density:colors[name] ? 1536 : 144}).trim().png().toBuffer();
    const logo = await sharp(trimmed).resize(216, 112, {fit:'inside'}).png().toBuffer();
    await sharp({create:{width:256, height:160, channels:4, background:'#ffffff'}})
      .composite([{input:logo, gravity:'centre'}]).png().toFile(path.join(root, name+'.png'));
  }
}
render().catch(error => { console.error(error); process.exitCode=1; });
