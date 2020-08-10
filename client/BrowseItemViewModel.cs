using Microsoft.WindowsAPICodePack.Shell;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
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
        }

        public string LocalPath => m_localPath;
        public string GameName { get; private set; }

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
    }
}
