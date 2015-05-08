using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Net;
using System.IO;
using System.Xml.Serialization;

namespace Common
{
    public static class Extensions
    {
        public static string GetPOSTBody(this HttpListenerRequest request)
        {
            string body;
            using (var s = new System.IO.StreamReader(request.InputStream, request.ContentEncoding))
            { body = s.ReadToEnd(); }
            return body;
        }

        public static Dictionary<string, string> GetPOSTParams(this HttpListenerRequest request)
        {
            string body;
            using (var s = new System.IO.StreamReader(request.InputStream, request.ContentEncoding))
            {
                body = s.ReadToEnd();
            }
            try
            {
                var ret = body.Split('&').Select(kvp =>
                {
                    var _t = kvp.Split('=');
                    return new KeyValuePair<string, string>(_t[0], _t[1]);
                }).ToDictionary(x => x.Key, x => x.Value);

                Console.WriteLine("post params:");
                foreach (var parname in ret.Keys)
                    Console.WriteLine("  {0}={1}", parname, ret[parname]);
                return ret;
            }
            catch (Exception)
            {
                return new Dictionary<string, string>();
            }
        }

        public static T1 GetKeyByValue<T1>(this Dictionary<T1, string> dict, string value)
        {
            foreach (var key in dict.Keys)
                if (dict[key] == value)
                    return key;
            return default(T1);
        }

        public static string SetError(this HttpListenerResponse response, HttpStatusCode code, string message)
        {
            response.StatusCode = (int)code;
            response.StatusDescription = message;
            return null;
        }

        public static void ToXML<T>(this T item, string filename)
        {
            using (var f = File.Open(filename, FileMode.Create))
                new XmlSerializer(typeof(T)).Serialize(f, item);
        }

        public static T FromXML<T>(string filename)
        {
            using (var f = File.Open(filename, FileMode.Open))
                return (T)new XmlSerializer(typeof(T)).Deserialize(f);
        }

        public static string[] GetVals(this Dictionary<string, string> d, string key)
        {
            if (d.ContainsKey(key))
                return d[key].Split(',');
            else
                return new string[] { };
        }
        public static string[] GetVals(this NameValueCollection d, string key)
        {
            if (d.AllKeys.Contains(key))
                return d[key].Split(',');
            else
                return new string[] { };
        }
        public static bool ContainsAny(this string s, IEnumerable<string> subs)
        {
            foreach (var ss in subs)
                if (s.Contains(ss)) return true;
            return subs.Count() == 0;
        }
        public static bool ContainsAny<T>(this IEnumerable<T> s, IEnumerable<T> subs)
        {
            foreach (var ss in subs)
                if (s.Contains(ss)) return true;
            return subs.Count() == 0;
        }
        public static bool ContainsAll<T>(this IEnumerable<T> s, IEnumerable<T> subs)
        {
            foreach (var ss in subs)
                if (!s.Contains(ss)) return false;
            return true;
        }
        public static void Log(HttpListenerRequest req)
        {
            Console.WriteLine("=============================");
            Console.WriteLine("REQUEST:");
            Console.WriteLine(req.Url);

            Console.WriteLine("get params:");
            foreach (var parname in req.QueryString.AllKeys)
                Console.WriteLine("  {0}={1}", parname, req.QueryString[parname]);
        }
        public static void Log(HttpListenerResponse res, string content)
        {
            Console.WriteLine("RESPONSE:");
            Console.WriteLine("  " + res.StatusCode.ToString());
            Console.WriteLine("  " + res.StatusDescription.ToString());
            Console.WriteLine("  " + content);
            Console.WriteLine("=============================");
        }
    }
}
