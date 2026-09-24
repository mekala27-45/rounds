import { forwardRef, type ComponentPropsWithoutRef } from "react";

/**
 * Use document navigation until the deployed Vinext client router is reliable.
 * Its production Link transition currently throws before changing the URL.
 * Native anchors also preserve keyboard navigation, new tabs and URL fragments.
 */
export const SiteLink = forwardRef<HTMLAnchorElement, ComponentPropsWithoutRef<"a">>(
  function SiteLink(props, ref) {
    return <a {...props} ref={ref} />;
  },
);
