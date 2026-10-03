import type { ReactNode, SVGProps } from 'react';

export type IconProps = Omit<SVGProps<SVGSVGElement>, 'children'>;

interface SvgProps extends IconProps {
  /** Descriptive name from docs/05_UI_SPEC.md §1 (`data-icon`, used by tests). */
  name: string;
  children: ReactNode;
}

/** Base for the inline icons: 24 px grid, stroke = currentColor, hidden from screen readers (text says it). */
export function Svg({ name, children, className = 'size-5', ...rest }: SvgProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-icon={name}
      className={className}
      {...rest}
    >
      {children}
    </svg>
  );
}
