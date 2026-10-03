import { useTranslation } from 'react-i18next';
import { CalendarIcon } from '../../components/icons/icons';
import { MobileLayout } from '../../components/MobileLayout';

export function ContractorLayout() {
  const { t } = useTranslation();
  return (
    <MobileLayout
      homePath="/contractor"
      items={[
        {
          to: '/contractor',
          label: t('nav.contractor.today'),
          icon: CalendarIcon,
          end: true,
          testId: 'nav-contractor-today',
        },
      ]}
    />
  );
}
