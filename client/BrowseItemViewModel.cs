using Microsoft.WindowsAPICodePack.Shell;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace GGShot
{
    class BrowseItemViewModel
    {
        private string m_localPath;

        public BrowseItemViewModel(string localPath)
        {
            m_localPath = localPath;
            string filename = Path.GetFileNameWithoutExtension(localPath);
            Regex nameMatcher = new Regex(@"([\w _]+) \d+[-_]\d+[-_]\d+ \d+[-_]\d+[-_]\d+");

            var match = nameMatcher.Match(filename);
            if (match.Success)
            {
                // Most likely character to get replaced in most game names is colon... May need
                // to special case otherwise.
                GameName = match.Groups[1].Value.Replace('_', ':');
            }
            else
            {
                GameName = "Unknown";
            }

            CreationTime = new FileInfo(m_localPath).CreationTimeUtc;
        }

        public string LocalPath => m_localPath;
        public string GameName { get; private set; }

        public DateTime CreationTime { get; private set; }

        public object ItemSource
        {
            get
            {
                if (m_localPath.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
                {
                    return new Uri(m_localPath);
                }
                else
                {
                    var sf = ShellFile.FromFilePath(m_localPath);
                    return sf.Thumbnail.ExtraLargeBitmapSource;
                }
            }
        }

        internal byte[] GetEncodedContentBytes()
        {
            Image bmp = Image.FromFile(LocalPath);
            double width = bmp.Width;
            double height = bmp.Height;
            if (width > 1920)
            {
                height = (height / width) * 1920;
                width = 1920;
            }

            if (height > 1080)
            {
                width = bmp.Width;
                height = bmp.Height;

                width = (width / height) * 1080;
                height = 1080;
            }

            Bitmap scaledBmp = new Bitmap(bmp, (int)width, (int)height);

            MemoryStream ms = new MemoryStream();

            EncoderParameters encodeParams = new EncoderParameters(1);

            encodeParams.Param[0] = new EncoderParameter(Encoder.Quality, 90L);
            ImageCodecInfo codec = GetEncoder(ImageFormat.Jpeg);
            scaledBmp.Save(ms, codec, encodeParams);

            return ms.ToArray();
        }

        private static ImageCodecInfo GetEncoder(ImageFormat format)
        {
            ImageCodecInfo[] codecs = ImageCodecInfo.GetImageDecoders();
            foreach (ImageCodecInfo codec in codecs)
            {
                if (codec.FormatID == format.Guid)
                {
                    return codec;
                }
            }
            return null;
        }
    }
}
