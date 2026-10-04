import type { ComponentType } from 'react';
import {
  DotsIcon,
  DrainIcon,
  DropletIcon,
  LampIcon,
  PotholeIcon,
  RoadCrackIcon,
  TrashIcon,
  WavesIcon,
} from '../../../components/icons/icons';
import type { IconProps } from '../../../components/icons/Svg';

// The 8 seeded categories (db/V1 complaint_categories); a category added later gets the neutral icon.
const BY_NAME: Record<string, ComponentType<IconProps>> = {
  Pothole: PotholeIcon,
  'Road Damage': RoadCrackIcon,
  'Garbage Accumulation': TrashIcon,
  Waterlogging: WavesIcon,
  'Water Leakage': DropletIcon,
  'Blocked Drain': DrainIcon,
  Streetlight: LampIcon,
  Other: DotsIcon,
};

export function CategoryIcon({ name, ...props }: IconProps & { name: string }) {
  const Icon = BY_NAME[name] ?? DotsIcon;
  return <Icon {...props} />;
}
