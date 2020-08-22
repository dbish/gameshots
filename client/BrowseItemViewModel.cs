using Microsoft.WindowsAPICodePack.Shell;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Reflection;
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

            if (Path.GetExtension(localPath) == ".png" ||
                Path.GetExtension(localPath) == ".jpg" ||
                Path.GetExtension(localPath) == ".jpeg")
            {
                IsPicture = true;
            }
            else if (Path.GetExtension(localPath) == ".mp4")
            {
                IsVideo = true;
            }
            else
            {
                // TODO: Throw exception? Set some IsInvalid flag? Something to let us filter this entry out
            }
        }

        public string LocalPath => m_localPath;
        public string GameName { get; private set; }
        public bool IsVideo { get; private set; }
        public bool IsPicture { get; private set; }

        public DateTime CreationTime { get; private set; }

        public object ItemSource
        {
            get
            {
                var sf = ShellFile.FromFilePath(m_localPath);
                return sf.Thumbnail.ExtraLargeBitmapSource;
            }
        }

        public Uri VideoSource => IsVideo ? new Uri(m_localPath) : null;

        internal byte[] GetEncodedContentBytes()
        {
            if (IsPicture)
            {
                return GetEncodedPictureBytes();
            }
            else if (IsVideo)
            {
                return GetEncodedVideoBytes();
            }
            else
            {
                throw new InvalidOperationException("Can only encode video or pictures");
            }
        }

        private byte[] GetEncodedVideoBytes()
        {
            // Example: ffmpeg.exe -i "C:\Users\timmi\Videos\Captures\Sea of Thieves 2020-08-02 23-27-06.mp4" -vf scale=-1:720 -b:v 600k -maxrate 900k output6.mp4
            string tempFile = Path.GetTempFileName() + ".mp4";
            string args = $"-y -i \"{LocalPath}\" -vf scale=-1:720 -b:v 600k -maxrate 600k \"{tempFile}\"";
            Process p = Process.Start(FFMpegPath, args);
            // TODO: Don't block the UI while we re-encode
            p.WaitForExit();
            var ret = File.ReadAllBytes(tempFile);
            File.Delete(tempFile);
            return ret;
        }

        private string FFMpegPath
        {
            get
            {
                string dir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                return Path.Combine(dir, "ffmpeg", "ffmpeg.exe");
            }
        }

        internal async Task<byte[]> GetTrimmedVideoBytesAsync(int clipStartMs, int clipEndMs)
        {
            return await Task.Run(
                () =>
                {
                    string startTime = MillisecondsToTimestamp(clipStartMs);
                    string totalTime = MillisecondsToTimestamp(clipEndMs - clipStartMs);
                    // Example: ffmpeg.exe -i "C:\Users\timmi\Videos\Captures\Sea of Thieves 2020-08-02 23-27-06.mp4" -vf scale=-1:720 -b:v 600k -maxrate 900k output6.mp4
                    string tempFile = Path.GetTempFileName() + ".mp4";
                    string args = $"-y -i \"{LocalPath}\" -vf scale=-1:720 -b:v 600k -maxrate 600k -ss {startTime} -t {totalTime} \"{tempFile}\"";

                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        Arguments = args,
                        CreateNoWindow = true,
                        FileName = FFMpegPath,
                        WindowStyle = ProcessWindowStyle.Hidden
                    };

                    Process p = Process.Start(psi);
                    // TODO: Don't block the UI while we re-encode
                    p.WaitForExit();
                    var ret = File.ReadAllBytes(tempFile);
                    File.Delete(tempFile);
                    return ret;
                });
        }

        private string MillisecondsToTimestamp(int ms)
        {
            int msPart = ms % 1000;
            int seconds = ms / 1000;
            int secPart = seconds % 60;
            int minutes = seconds / 60;

            return $"00:{minutes:00}:{secPart:00}.{msPart:0000}";
        }

        private byte[] GetEncodedPictureBytes()
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
