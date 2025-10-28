// @ts-check
import { defineConfig, passthroughImageService } from "astro/config";
import starlight from "@astrojs/starlight";
import starlightImageZoom from "starlight-image-zoom";
import rehypeExternalLinks from "rehype-external-links";

// https://astro.build/config
export default defineConfig({
  image: {
    service: passthroughImageService(),
  },
  integrations: [
    starlight({
      expressiveCode: {
        themes: ["nord", "catppuccin-latte"],
        defaultProps: {
          wrap: true,
        },
      },
      plugins: [starlightImageZoom()],
      customCss: [
        // Relative path to your @font-face CSS file.
        "./src/fonts/font-face.css",
        // Relative path to your custom CSS file
        "./src/styles/custom.css",
      ],
      title: "Vibe Coding with AWS MCP Servers",
      favicon: "favicon.ico",
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      logo: {
        dark: "./src/assets/logo_pace_white.webp",
        light: "./src/assets/logo_pace_black.webp",
        replacesTitle: true,
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers",
        },
      ],
      sidebar: [
        {
          label: "Start Here",
          items: [{ label: "Getting Started", link: "/intro/getting-started/" }],
        },
        {
          label: "Development Environments",
          items: [
            {
              label: "Prerequisites",
              link: "/intro/prerequisites",
            },
            {
              label: "Setup your own development environment",
              link: "/dev-env/development-environment-setup",
            },
            {
              label: "Setup your IDE Extensions",
              link: "/dev-env/ide-extensions-setup",
            },
          ],
        },
        {
          label: "Workshop",
          items: [
            { label: "Overview", link: "/workshop/overview/" },
            { label: "1. Discovery & Analysis Section", link: "/workshop/phase-1/" },
            {
              label: "2. Implementation Deep Dive Section",
              link: "/workshop/phase-2/",
            },
            {
              label: "3. Production Readiness Assessment Section",
              link: "/workshop/phase-3/",
            },
            { label: "Wrap-up", link: "/workshop/wrap-up/" },
          ],
        },
        {
          label: "Help",
          items: [
            { label: "Troubleshooting Guide", link: "/faq/troubleshooting/" },
            {
              label: "AWS MCP Frontend Activity Troubleshooting",
              link: "/faq/frontend-troubleshooting/",
            },
            { label: "References", link: "/faq/references/" },
          ],
        },
        {
          label: "Appendix",
          items: [{ label: "Cleanup", link: "/dev-env/cleanup" }],
        },
      ],
    }),
  ],
  vite: {
    ssr: {
      noExternal: ["entities"],
    },
  },
  markdown: {
    rehypePlugins: [
      [
        rehypeExternalLinks,
        {
          target: "_blank", // Ensures links open in a new tab
          rel: ["noopener", "noreferrer"], // Important for security
          // Optional: Add content to external links, e.g., an icon
          // content: { type: "text", value: " 🔗" },
        },
      ],
    ],
  },
});
