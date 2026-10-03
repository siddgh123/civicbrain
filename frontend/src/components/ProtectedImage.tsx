import { useEffect, useState, type ImgHTMLAttributes } from 'react';
import { useTranslation } from 'react-i18next';
import { getAccessToken } from '../auth/tokenStore';
import { API_BASE } from '../lib/api';
import { AlertIcon } from './icons/icons';

interface ProtectedImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  /** `complaint_images.id` → GET /api/v1/files/{imageId} (04 §4). */
  imageId: number;
  alt: string;
}

type Loaded = { imageId: number; url: string } | { imageId: number; failed: true };

/**
 * docs/05_UI_SPEC.md §2 + rule 20: photos are fetched with the bearer header and shown as blob URLs (never a
 * public URL), and each blob URL is revoked when the image changes or unmounts. Used from P11.
 */
export function ProtectedImage({ imageId, alt, className, ...img }: ProtectedImageProps) {
  const { t } = useTranslation();
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let url: string | null = null;
    const token = getAccessToken();
    fetch(`${API_BASE}/files/${imageId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: controller.signal,
    })
      .then(async (response) => {
        const blob = response.ok ? await response.blob() : null;
        if (blob === null || !blob.type.startsWith('image/')) throw new Error(`image ${imageId}: ${response.status}`);
        url = URL.createObjectURL(blob);
        setLoaded({ imageId, url });
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoaded({ imageId, failed: true });
      });
    return () => {
      controller.abort();
      if (url !== null) URL.revokeObjectURL(url);
    };
  }, [imageId]);

  const current = loaded?.imageId === imageId ? loaded : null;
  if (current === null) {
    return (
      <div
        role="img"
        aria-busy="true"
        aria-label={alt}
        className={`bg-slate-200 motion-safe:animate-pulse ${className ?? ''}`}
      />
    );
  }
  if ('failed' in current) {
    return (
      <div role="img" aria-label={alt} className={`grid place-items-center bg-slate-100 text-slate-500 ${className ?? ''}`}>
        <AlertIcon className="size-6" />
        <span className="sr-only">{t('errors.NOT_FOUND')}</span>
      </div>
    );
  }
  return <img src={current.url} alt={alt} className={className} {...img} />;
}
