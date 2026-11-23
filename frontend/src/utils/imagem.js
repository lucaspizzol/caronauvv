// ==========================================================
// Foto de perfil: o navegador recorta em quadrado e reduz ANTES de enviar.
// Uma foto de celular (3-8 MB) vira um JPEG de ~30 KB: o envio fica rapido
// ate no 4G e o banco nao enche. O servidor confere tudo de novo (auth/foto.py).
// ==========================================================
export const LADO_FOTO = 400 // pixels do lado da foto que vai para o servidor
export const TIPOS_ACEITOS = ['image/jpeg', 'image/png', 'image/webp']
export const TAMANHO_MAXIMO_MB = 15 // do arquivo original, antes de reduzir

/** Mensagem de erro para um arquivo que nao serve como foto, ou '' se estiver tudo certo. */
export function validarArquivoDeFoto(arquivo) {
  if (!arquivo) return 'Escolha uma foto.'
  if (!TIPOS_ACEITOS.includes(arquivo.type)) return 'Use uma foto em JPG, PNG ou WebP.'
  if (arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024) return `A foto passou de ${TAMANHO_MAXIMO_MB} MB.`
  return ''
}

/**
 * Maior quadrado que cabe no meio da imagem.
 * Ex.: foto deitada 4000 x 3000 -> corta 500 px de cada lado: { x: 500, y: 0, lado: 3000 }
 */
export function recorteCentral(largura, altura) {
  const lado = Math.min(largura, altura)
  return { x: Math.floor((largura - lado) / 2), y: Math.floor((altura - lado) / 2), lado }
}

async function carregar(arquivo) {
  // createImageBitmap ja gira a foto conforme o celular foi segurado (EXIF)
  if (window.createImageBitmap) {
    try {
      return await createImageBitmap(arquivo, { imageOrientation: 'from-image' })
    } catch {
      /* navegador antigo: cai no <img> abaixo */
    }
  }
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(arquivo)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Não deu para abrir essa imagem. Tente outra foto.'))
    }
    img.src = url
  })
}

/** Recorta no centro, reduz para LADO_FOTO e devolve um Blob JPEG pronto para o upload. */
export async function prepararFoto(arquivo, lado = LADO_FOTO) {
  const imagem = await carregar(arquivo)
  const corte = recorteCentral(imagem.width, imagem.height)
  const tela = document.createElement('canvas')
  tela.width = tela.height = Math.min(lado, corte.lado)
  const ctx = tela.getContext('2d')
  ctx.fillStyle = '#ffffff' // PNG transparente vira fundo branco no JPEG
  ctx.fillRect(0, 0, tela.width, tela.height)
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(imagem, corte.x, corte.y, corte.lado, corte.lado, 0, 0, tela.width, tela.height)
  imagem.close?.()
  return new Promise((resolve, reject) => {
    tela.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Não deu para preparar a foto.'))), 'image/jpeg', 0.85)
  })
}
