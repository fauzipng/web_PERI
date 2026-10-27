// =====================================================================
// DATA UJI UNTUK EVALUASI — CONTOH / DEMO SAJA
// TODO: Ganti dengan profil uji & ground truth asli dari penilaian pengurus PERI
// (bisa diimpor lewat halaman admin: format { profiles: [...], ground_truth: [...] }).
// Rating admin: 0 = tidak sesuai ... 3 = sangat sesuai. Relevan jika rating >= ambang (default 2).
// =====================================================================
export const TEST_PROFILES = [
  { id: 1, age: 28, employment_status: 'irt', economic_condition: 'kurang_mampu', interests: ['keterampilan_tangan', 'kesehatan_keluarga'], goals: ['penghasilan_tambahan'] },
  { id: 2, age: 19, employment_status: 'pelajar', economic_condition: 'menengah', interests: ['kesetaraan_gender', 'kepemimpinan'], goals: ['pengembangan_diri', 'jejaring'] },
  { id: 3, age: 30, employment_status: 'wirausaha', economic_condition: 'menengah', interests: ['pemasaran_digital', 'kewirausahaan'], goals: ['peluang_usaha'] },
  { id: 4, age: 24, employment_status: 'belum_bekerja', economic_condition: 'kurang_mampu', interests: ['literasi_digital', 'keterampilan_tangan'], goals: ['tambah_keterampilan', 'penghasilan_tambahan'] },
  { id: 5, age: 42, employment_status: 'karyawan', economic_condition: 'mapan', interests: ['sosial_lingkungan', 'kepemimpinan'], goals: ['kontribusi_sosial', 'jejaring'] },
  { id: 6, age: 55, employment_status: 'irt', economic_condition: 'menengah', interests: ['kesehatan_keluarga', 'keterampilan_tangan'], goals: ['tambah_keterampilan'] },
  { id: 7, age: 22, employment_status: 'karyawan', economic_condition: 'menengah', interests: ['pemasaran_digital', 'literasi_digital'], goals: ['tambah_keterampilan', 'pengembangan_diri'] },
  { id: 8, age: 35, employment_status: 'wirausaha', economic_condition: 'kurang_mampu', interests: ['kewirausahaan', 'keterampilan_tangan'], goals: ['peluang_usaha', 'penghasilan_tambahan'] },
];

const gt = (profile_id, rows) => rows.map(([program_id, admin_rating]) => ({ profile_id, program_id, admin_rating }));
export const GROUND_TRUTH = [
  ...gt(1, [[1, 3], [4, 3], [5, 2]]), ...gt(2, [[2, 3], [6, 2], [3, 1]]),
  ...gt(3, [[5, 3], [3, 3]]),         ...gt(4, [[3, 2], [4, 3], [1, 2]]),
  ...gt(5, [[6, 3], [2, 1]]),         ...gt(6, [[4, 3], [1, 3]]),
  ...gt(7, [[3, 3], [2, 2]]),         ...gt(8, [[5, 3], [1, 3], [4, 2]]),
];
