// Loads the brand font for TitleCard and ProductTag before any frame renders.
// fontFile is a path inside the Remotion project's public folder, e.g. "fonts/Montserrat-Bold.ttf".
// Leave it empty to use a font installed on the computer.
// A missing or broken font file stops the render with an error instead of silently
// falling back to another font.
import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";

export const useBrandFont = (family: string, fontFile?: string) => {
  const [handle] = useState(() => (fontFile ? delayRender(`Loading font ${fontFile}`) : null));
  useEffect(() => {
    if (!fontFile || handle === null) return;
    new FontFace(family, `url(${staticFile(fontFile)})`)
      .load()
      .then((face) => {
        document.fonts.add(face);
        continueRender(handle);
      })
      .catch((err) => cancelRender(new Error(`Could not load font ${fontFile}: ${err}`)));
  }, [family, fontFile, handle]);
};
