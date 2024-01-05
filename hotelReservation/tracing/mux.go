// Copyright (c) 2017 Uber Technologies, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package tracing

import (
	"google.golang.org/grpc/metadata"
	"net/http"

	opentracing "github.com/opentracing/opentracing-go"
)

func tracingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		tracingHeaders := []string{
			"x-request-id",
			"x-b3-traceid",
			"x-b3-spanid",
			"x-b3-sampled",
			"x-b3-parentspanid",
			"x-b3-flags",
			"x-ot-span-context",
		}
		for _, key := range tracingHeaders {
			if val := r.Header.Get(key); val != "" {
				ctx = metadata.AppendToOutgoingContext(ctx, key, val)
			}
		}
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// NewServeMux creates a new TracedServeMux.
func NewServeMux(tracer opentracing.Tracer) *TracedServeMux {
	return &TracedServeMux{
		mux:    http.NewServeMux(),
		tracer: tracer,
	}
}

// TracedServeMux is a wrapper around http.ServeMux that instruments handlers for tracing.
type TracedServeMux struct {
	mux    *http.ServeMux
	tracer opentracing.Tracer
}

// Handle implements http.ServeMux#Handle
func (tm *TracedServeMux) Handle(pattern string, handler http.Handler) {
	tm.mux.Handle(pattern, tracingMiddleware(handler))
	//middleware := nethttp.Middleware(
	//	tm.tracer,
	//	handler,
	//	nethttp.OperationNameFunc(func(r *http.Request) string {
	//		return "HTTP " + r.Method + " " + pattern
	//	}))
	//tm.mux.Handle(pattern, middleware)
}

// ServeHTTP implements http.ServeMux#ServeHTTP
func (tm *TracedServeMux) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	tm.mux.ServeHTTP(w, r)
}
