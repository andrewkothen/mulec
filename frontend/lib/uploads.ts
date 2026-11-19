const extensions = /\.(wav|mp3|flac|m4a|ogg|aiff|aif)$/i;
export const AUDIO_ACCEPT = ".wav,.mp3,.flac,.m4a,.ogg,.aiff,.aif";
export const fileKey = (file: File) =>
  `${file.name}\0${file.size}\0${file.lastModified}`;

export function selectAudioFiles(existing: File[], incoming: File[]) {
  const files = [...existing],
    rejected: string[] = [];
  const seen = new Set(files.map(fileKey));
  for (const file of incoming) {
    if (!extensions.test(file.name))
      rejected.push(`${file.name}: unsupported audio format`);
    else if (!file.size) rejected.push(`${file.name}: file is empty`);
    else if (file.size > 150 * 1024 * 1024)
      rejected.push(`${file.name}: exceeds 150 MB`);
    else if (!seen.has(fileKey(file))) {
      seen.add(fileKey(file));
      files.push(file);
    }
  }
  return { files, rejected };
}
