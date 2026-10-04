import { Svg, type IconProps } from './Svg';

// Hand-drawn inline icons (no icon package, docs/05_UI_SPEC.md §1). Status icons first, then UI icons.

export function InboxIcon(props: IconProps) {
  return (
    <Svg name="inbox" {...props}>
      <path d="M3 13h5l1.5 3h5L16 13h5" />
      <path d="M5.5 5h13L21 13v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5z" />
    </Svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Svg name="search" {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </Svg>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <Svg name="calendar" {...props}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </Svg>
  );
}

export function UserCheckIcon(props: IconProps) {
  return (
    <Svg name="user-check" {...props}>
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21a7 7 0 0 1 14 0" />
      <path d="m16 11 2 2 4-4" />
    </Svg>
  );
}

export function ClipboardIcon(props: IconProps) {
  return (
    <Svg name="clipboard" {...props}>
      <rect x="5" y="4" width="14" height="18" rx="2" />
      <path d="M9 2h6v4H9zM9 12h6M9 16h4" />
    </Svg>
  );
}

export function HammerIcon(props: IconProps) {
  return (
    <Svg name="hammer" {...props}>
      <path d="m13 8-9 9a2 2 0 0 0 3 3l9-9" />
      <path d="m11 6 4-4 7 7-4 4z" />
    </Svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Svg name="check" {...props}>
      <path d="m5 12 5 5 9-10" />
    </Svg>
  );
}

export function CheckDoubleIcon(props: IconProps) {
  return (
    <Svg name="check-double" {...props}>
      <path d="m2 12 5 5 9-10" />
      <path d="m11.5 16.5.5.5 9-10" />
    </Svg>
  );
}

export function RotateIcon(props: IconProps) {
  return (
    <Svg name="rotate" {...props}>
      <path d="M3 12a9 9 0 1 0 2.6-6.4L3 8" />
      <path d="M3 3v5h5" />
    </Svg>
  );
}

export function XIcon(props: IconProps) {
  return (
    <Svg name="x" {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Svg>
  );
}

export function LinkIcon(props: IconProps) {
  return (
    <Svg name="link" {...props}>
      <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.5-1.5" />
    </Svg>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <Svg name="home" {...props}>
      <path d="M3 11 12 3l9 8" />
      <path d="M5 10v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V10" />
      <path d="M10 21v-6h4v6" />
    </Svg>
  );
}

export function CameraIcon(props: IconProps) {
  return (
    <Svg name="camera" {...props}>
      <path d="M3 8a2 2 0 0 1 2-2h3l2-3h4l2 3h3a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <circle cx="12" cy="13" r="4" />
    </Svg>
  );
}

export function ListIcon(props: IconProps) {
  return (
    <Svg name="list" {...props}>
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </Svg>
  );
}

export function GridIcon(props: IconProps) {
  return (
    <Svg name="grid" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </Svg>
  );
}

export function RouteIcon(props: IconProps) {
  return (
    <Svg name="route" {...props}>
      <circle cx="6" cy="19" r="2" />
      <circle cx="18" cy="5" r="2" />
      <path d="M8 19h8.5a3.5 3.5 0 0 0 0-7h-9a3.5 3.5 0 0 1 0-7H16" />
    </Svg>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <Svg name="users" {...props}>
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21a7 7 0 0 1 14 0M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-4-6.3" />
    </Svg>
  );
}

export function ShieldIcon(props: IconProps) {
  return (
    <Svg name="shield" {...props}>
      <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />
    </Svg>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Svg name="logout" {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
    </Svg>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <Svg name="alert" {...props}>
      <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <path d="M12 9v4M12 17h.01" />
    </Svg>
  );
}

export function WifiOffIcon(props: IconProps) {
  return (
    <Svg name="wifi-off" {...props}>
      <path d="m2 2 20 20M8.5 16.5a5 5 0 0 1 7 0M5 12.5a10 10 0 0 1 5-2.8M19 12.5a10 10 0 0 0-2.2-1.6M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8A15 15 0 0 0 11 5M12 20h.01" />
    </Svg>
  );
}

export function BellIcon(props: IconProps) {
  return (
    <Svg name="bell" {...props}>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 0 0 4 0" />
    </Svg>
  );
}

export function ScanIcon(props: IconProps) {
  return (
    <Svg name="scan" {...props}>
      <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10" />
    </Svg>
  );
}

export function MapPinIcon(props: IconProps) {
  return (
    <Svg name="map-pin" {...props}>
      <path d="M12 21s-7-7.6-7-12a7 7 0 0 1 14 0c0 4.4-7 12-7 12z" />
      <circle cx="12" cy="9" r="2.5" />
    </Svg>
  );
}

// Category tiles (docs/05_UI_SPEC.md §4 step 1).

export function PotholeIcon(props: IconProps) {
  return (
    <Svg name="pothole" {...props}>
      <path d="M2 17h20" />
      <path d="M6 17c1-3.5 3-5 6-5s5 1.5 6 5" />
      <path d="M9 14.5l1 1.5M14 13.5l-1 2" />
    </Svg>
  );
}

export function RoadCrackIcon(props: IconProps) {
  return (
    <Svg name="road-crack" {...props}>
      <path d="M6 21 9 3M18 21 15 3" />
      <path d="M12 6l-1 3 2 2-1.5 3 1 3-.5 3" />
    </Svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <Svg name="trash" {...props}>
      <path d="M4 7h16M9 7V4h6v3" />
      <path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" />
      <path d="M10 11v6M14 11v6" />
    </Svg>
  );
}

export function WavesIcon(props: IconProps) {
  return (
    <Svg name="waves" {...props}>
      <path d="M2 9c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0" />
      <path d="M2 14c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0" />
      <path d="M2 19c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0" />
    </Svg>
  );
}

export function DropletIcon(props: IconProps) {
  return (
    <Svg name="droplet" {...props}>
      <path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z" />
    </Svg>
  );
}

export function DrainIcon(props: IconProps) {
  return (
    <Svg name="drain" {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M7 5v14M11 5v14M15 5v14M19 5v14" />
    </Svg>
  );
}

export function LampIcon(props: IconProps) {
  return (
    <Svg name="lamp" {...props}>
      <path d="M8 21h8M12 21V8" />
      <path d="M12 8c0-3 2-5 5-5h1" />
      <path d="M16 3h4l-1 4h-2z" />
    </Svg>
  );
}

export function DotsIcon(props: IconProps) {
  return (
    <Svg name="dots" {...props}>
      <circle cx="6" cy="12" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="18" cy="12" r="1.5" />
    </Svg>
  );
}
