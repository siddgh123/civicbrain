import { useTranslation } from 'react-i18next';
import { CameraIcon, HomeIcon, ListIcon } from '../../components/icons/icons';
import { MobileLayout } from '../../components/MobileLayout';

export function CitizenLayout() {
  const { t } = useTranslation();
  return (
    <MobileLayout
      homePath="/citizen"
      items={[
        { to: '/citizen', label: t('nav.citizen.home'), icon: HomeIcon, end: true, testId: 'nav-citizen-home' },
        { to: '/citizen/new', label: t('nav.citizen.report'), icon: CameraIcon, testId: 'nav-citizen-report' },
        {
          to: '/citizen/complaints',
          label: t('nav.citizen.complaints'),
          icon: ListIcon,
          testId: 'nav-citizen-complaints',
        },
      ]}
    />
  );
}
