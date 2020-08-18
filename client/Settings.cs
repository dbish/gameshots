using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace GGShot
{
    class Settings
    {
        public string UserName { get; set; }
        public string AccessToken { get; set; }

        public DateTime TokenExpiration { get; set; }


        public Settings()
        {
        }

        private string SettingsDir => Environment.ExpandEnvironmentVariables("%LOCALAPPDATA%\\gameshots");
        private string SettingsFile => Path.Combine(SettingsDir, "settings.json");

        public void Save()
        {
            Directory.CreateDirectory(SettingsDir);
            File.WriteAllText(SettingsFile, JsonConvert.SerializeObject(this));
        }

        public void Load()
        {
            try
            {
                var settings = JsonConvert.DeserializeObject<Settings>(File.ReadAllText(SettingsFile));
                this.UserName = settings.UserName;
                this.AccessToken = settings.AccessToken;
                this.TokenExpiration = settings.TokenExpiration;
            }
            catch (IOException)
            {
                // File doesn't exist or something. Ignore.
            }
        }

    }
}
