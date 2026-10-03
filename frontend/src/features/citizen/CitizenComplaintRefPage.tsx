import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router';
import { PlaceholderPage } from '../../components/PlaceholderPage';

export function CitizenComplaintRefPage() {
  const { t } = useTranslation();
  const { publicRef = '' } = useParams();
  return <PlaceholderPage title={t('pages.track', { publicRef })} />;
}
