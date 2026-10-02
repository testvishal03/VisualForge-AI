/** Font files imported by the bundler resolve to their URL. */
declare module '*.woff2' {
  const url: string;
  export default url;
}
