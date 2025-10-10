// scripts/ai_schedule_postprocess.js
const { spawnSync } = require('child_process');

if (process.argv.length < 4) {
  console.error("Usage: node scripts/ai_schedule_postprocess.js <input_xml> <output_xml> [gantt_json] [explanations_json] [excel_out]");
  process.exit(2);
}

const args = ['ai_schedule_postprocess.py', ...process.argv.slice(2)];
const res = spawnSync('python', args, { stdio: 'inherit' });
process.exit(res.status || 0);
