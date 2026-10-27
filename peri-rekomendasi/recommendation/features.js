// Definisi ruang fitur. SATU sumber kebenaran untuk profil DAN program,
// sehingga Cosine & Euclidean memakai dimensi yang persis sama.
export const FEATURE_GROUPS = {
  age: { label: 'Usia', type: 'single', options: [
    { id: '<=20', label: '20 tahun ke bawah' }, { id: '21-35', label: '21–35 tahun' },
    { id: '36-50', label: '36–50 tahun' }, { id: '>50', label: 'di atas 50 tahun' } ] },
  employment: { label: 'Status pekerjaan', type: 'single', options: [
    { id: 'pelajar', label: 'Pelajar/Mahasiswa' }, { id: 'irt', label: 'Ibu Rumah Tangga' },
    { id: 'karyawan', label: 'Karyawan' }, { id: 'wirausaha', label: 'Wirausaha' },
    { id: 'belum_bekerja', label: 'Belum bekerja' }, { id: 'lainnya', label: 'Lainnya' } ] },
  economic: { label: 'Kondisi ekonomi', type: 'single', options: [
    { id: 'kurang_mampu', label: 'Kurang mampu' }, { id: 'menengah', label: 'Menengah' }, { id: 'mapan', label: 'Mapan' } ] },
  interests: { label: 'Minat', type: 'multi', options: [
    { id: 'pemasaran_digital', label: 'Pemasaran digital' }, { id: 'kewirausahaan', label: 'Kewirausahaan' },
    { id: 'keterampilan_tangan', label: 'Keterampilan tangan' }, { id: 'literasi_digital', label: 'Literasi digital' },
    { id: 'kesetaraan_gender', label: 'Kesetaraan & hak perempuan' }, { id: 'kepemimpinan', label: 'Kepemimpinan' },
    { id: 'sosial_lingkungan', label: 'Kegiatan sosial & lingkungan' }, { id: 'kesehatan_keluarga', label: 'Kesehatan keluarga' } ] },
  goals: { label: 'Tujuan', type: 'multi', options: [
    { id: 'tambah_keterampilan', label: 'Menambah keterampilan' }, { id: 'peluang_usaha', label: 'Membuka peluang usaha' },
    { id: 'penghasilan_tambahan', label: 'Mendapat penghasilan tambahan' }, { id: 'jejaring', label: 'Memperluas jejaring' },
    { id: 'pengembangan_diri', label: 'Mengembangkan diri' }, { id: 'kontribusi_sosial', label: 'Berkontribusi untuk sosial' } ] },
};

// Bobot tiap kelompok fitur (default sama rata). Ubah di sini untuk eksperimen penelitian.
export const GROUP_WEIGHTS = { age: 1, employment: 1, economic: 1, interests: 1, goals: 1 };

export const labelOf = (group, id) => FEATURE_GROUPS[group].options.find(o => o.id === id)?.label ?? id;

// Normalisasi L2 per kelompok fitur (OPSIONAL, default mati).
// PENTING: bila dinyalakan, semua vektor memiliki panjang sama sehingga Cosine dan Euclidean
// selalu menghasilkan RANKING IDENTIK dan perbandingan kedua metode tidak lagi bermakna.
export const NORMALIZE_GROUPS = false;
